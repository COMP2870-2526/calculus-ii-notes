import numpy as np

# ============================================================
# Pure NumPy neural network for MNIST
# One input layer, one hidden layer, one output layer
#
# Terminology is chosen to match calculus notes first:
# - iterations           (epochs)
# - alpha                (learning rate)
# - objective            (loss)
# - gradient via chain rule (backpropagation)
# - parameter matrices   (weights)
# - offset vectors       (biases)
# ============================================================

# ----------------------------
# Data cache and file names
# ----------------------------
cache_directory = ".mnist_cache"

base_urls = [
    "https://storage.googleapis.com/cvdf-datasets/mnist/",
    "https://ossci-datasets.s3.amazonaws.com/mnist/",
]

training_images_file = "train-images-idx3-ubyte.gz"
training_targets_file = "train-labels-idx1-ubyte.gz"
test_images_file = "t10k-images-idx3-ubyte.gz"
test_targets_file = "t10k-labels-idx1-ubyte.gz"

# ----------------------------
# Dimensions and parameters
# ----------------------------
input_dimension = 28 * 28
hidden_dimension = 64
output_dimension = 10

iterations = 1000  # epochs
alpha = 1.0  # learning rate
seed = 42


# ----------------------------
# Download and cache data
# ----------------------------
def data_source():
    return np.lib.npyio.DataSource(cache_directory)


def fetch_bytes(file_name):
    ds = data_source()
    last_error = None

    for base_url in base_urls:
        try:
            with ds.open(base_url + file_name, "rb") as file_handle:
                return file_handle.read()
        except Exception as error:
            last_error = error

    raise RuntimeError(
        "Could not download " + file_name + ". Last error: " + str(last_error)
    )


def parse_idx_images(raw_bytes):
    magic_number = int.from_bytes(raw_bytes[0:4], "big")
    if magic_number != 2051:
        raise ValueError(
            "Invalid image file magic number: " + str(magic_number)
        )

    number_of_images = int.from_bytes(raw_bytes[4:8], "big")
    number_of_rows = int.from_bytes(raw_bytes[8:12], "big")
    number_of_columns = int.from_bytes(raw_bytes[12:16], "big")

    images = np.frombuffer(raw_bytes, dtype=np.uint8, offset=16)
    images = images.reshape(
        number_of_images, number_of_rows * number_of_columns
    )
    images = images.astype(np.float32) / 255.0
    return images


def parse_idx_targets(raw_bytes):
    magic_number = int.from_bytes(raw_bytes[0:4], "big")
    if magic_number != 2049:
        raise ValueError(
            "Invalid target file magic number: " + str(magic_number)
        )

    number_of_targets = int.from_bytes(raw_bytes[4:8], "big")
    targets = np.frombuffer(raw_bytes, dtype=np.uint8, offset=8)

    if targets.shape[0] != number_of_targets:
        raise ValueError("Target count mismatch")

    return targets.astype(np.int64)


def load_mnist():
    print("Loading MNIST (download once, then use cached files)...")

    training_inputs = parse_idx_images(fetch_bytes(training_images_file))
    training_targets = parse_idx_targets(fetch_bytes(training_targets_file))
    test_inputs = parse_idx_images(fetch_bytes(test_images_file))
    test_targets = parse_idx_targets(fetch_bytes(test_targets_file))

    return training_inputs, training_targets, test_inputs, test_targets


# ----------------------------
# Basic functions
# ----------------------------
def indicator_matrix(targets, number_of_classes=10):
    # convert one label per image to a 10 dimensional output for comparison
    matrix = np.zeros((number_of_classes, targets.shape[0]), dtype=np.float32)
    matrix[targets, np.arange(targets.shape[0])] = 1.0
    return matrix


def sigma(t):
    # sigmoid activation
    return 1.0 / (1.0 + np.exp(-t))


def sigma_prime_from_value(sigma_value):
    # derivative of sigmoid when the sigmoid value is already known
    return sigma_value * (1.0 - sigma_value)


def objective(z, targets):
    L = indicator_matrix(targets, number_of_classes=z.shape[0])
    return 0.5 * np.mean(np.sum((L - z) ** 2, axis=0))


def classification_accuracy(z, targets):
    predicted_targets = np.argmax(z, axis=0)
    return np.mean(predicted_targets == targets)


# ----------------------------
# Parameter initialisation
# ----------------------------


def initialise_parameters(random_number_generator):
    A = random_number_generator.normal(
        0.0,
        np.sqrt(1.0 / input_dimension),
        size=(hidden_dimension, input_dimension),
    ).astype(np.float32)

    a = np.zeros((hidden_dimension,), dtype=np.float32)

    B = random_number_generator.normal(
        0.0,
        np.sqrt(1.0 / hidden_dimension),
        size=(output_dimension, hidden_dimension),
    ).astype(np.float32)

    b = np.zeros((output_dimension,), dtype=np.float32)

    return A, a, B, b


# ----------------------------
# Forward map
# ----------------------------
def forward_map(x, A, a, B, b):
    # broadcast multiplication in all values at the same time using [:, None]
    r = A @ x + a[:, None]
    y = sigma(r)

    s = B @ y + b[:, None]
    z = sigma(s)

    return (r, y, s, z)


def predict(x, A, a, B, b):
    _, _, _, z = forward_map(x, A, a, B, b)
    return np.argmax(z, axis=0)


def evaluate(x, targets, A, a, B, b):
    _, _, _, z = forward_map(x, A, a, B, b)
    current_objective = objective(z, targets)
    current_accuracy = classification_accuracy(z, targets)
    return current_objective, current_accuracy


# ----------------------------
# Gradient descent
# ----------------------------
def train_network(x, targets, test_inputs, test_targets):
    random_number_generator = np.random.default_rng(seed)

    A, a, B, b = initialise_parameters(random_number_generator)

    L = indicator_matrix(targets, output_dimension)
    N = x.shape[1]

    for step in range(1, iterations + 1):
        # Forward map
        (_, y, _, z) = forward_map(x, A, a, B, b)
        current_objective = objective(z, targets)

        # --------------------------------------------------------
        # Gradient via chain rule (backpropagation)
        # --------------------------------------------------------
        sigma_p_z = sigma_prime_from_value(z)
        sigma_p_y = sigma_prime_from_value(y)

        # gradient of objective wrt to s
        dF_ds = ((z - L) * sigma_p_z) / N  # componentwise multiply

        # Gradients for the second parameter matrix and offset vector
        # dF / dB
        dF_dB = dF_ds @ y.T
        # dF / db
        dF_db = np.sum(dF_ds, axis=1)

        # Move the gradient back to the hidden layer
        # dF / dy
        dF_dy = B.T @ dF_ds

        # Gradient of objective wrt to r
        # dF / dr
        dF_dr = dF_dy * sigma_p_y  # component wise multiply

        # Gradients for the first parameter matrix and offset vector
        # dF / dA
        dF_dA = dF_dr @ x.T
        # dF / da
        dF_da = np.sum(dF_dr, axis=1)

        # --------------------------------------------------------
        # Gradient descent step
        # --------------------------------------------------------
        A = A - alpha * dF_dA
        a = a - alpha * dF_da
        B = B - alpha * dF_dB
        b = b - alpha * dF_db

        # test on training data
        (_, _, _, z) = forward_map(x, A, a, B, b)
        current_objective = objective(z, targets)

        # test on test data
        test_objective, test_accuracy = evaluate(
            test_inputs, test_targets, A, a, B, b
        )

        print(
            f"iteration {step:4d} / {iterations:4d} |"
            f" objective: {current_objective:.6e} | "
            f" test objective: {test_objective:.6e} | "
            f" test accuracy: {100.0 * test_accuracy:.2f}% "
        )

    return (A, a, B, b)


# ----------------------------
# Main programme
# ----------------------------
def main():
    training_inputs, training_targets, test_inputs, test_targets = load_mnist()

    # take transpose so that each column is a flattened image
    training_inputs = training_inputs.T
    test_inputs = test_inputs.T

    print("training inputs shape:", training_inputs.shape)
    print("training targets shape:", training_targets.shape)
    print("test inputs shape:    ", test_inputs.shape)
    print("test targets shape:   ", test_targets.shape)
    print()

    A, a, B, b = train_network(
        training_inputs,
        training_targets,
        test_inputs,
        test_targets,
    )

    final_objective, final_accuracy = evaluate(
        test_inputs, test_targets, A, a, B, b
    )

    print()
    print(f"Final test objective: {final_objective:.6f}")
    print(f"Final test accuracy:  {100.0 % final_accuracy:.2f}%")

    first_predictions = predict(test_inputs[:, :20], A, a, B, b)

    print()
    print("First 20 predictions: ", first_predictions)
    print("First 20 true values: ", test_targets[:20])


if __name__ == "__main__":
    main()
