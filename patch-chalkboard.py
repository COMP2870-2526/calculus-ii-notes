#!/usr/bin/env python

import pathlib
import sys

plugin_files = list(pathlib.Path(".").glob("**/reveal-chalkboard/plugin.js"))
css_files = list(pathlib.Path(".").glob("**/reveal-chalkboard/style.css"))

if not plugin_files:
    print("ERROR: no reveal-chalkboard/plugin.js found — run after quarto render", file=sys.stderr)
    sys.exit(1)

for f in plugin_files:
    patched = f.read_text()

    # Fix touchend eraser-lock: stopErasing() was missing from touchend handler
    # (mouseup calls it correctly, but touchend didn't — erasing mode got stuck on iPad)
    patched = patched.replace(
        "drawingCanvas[ mode ].sponge.style.visibility = 'hidden';\n\t\t\tstopDrawing();\n\t\t}, false )",
        "drawingCanvas[ mode ].sponge.style.visibility = 'hidden';\n\t\t\tstopDrawing();\n\t\t\tstopErasing();\n\t\t}, false )",
        1,
    )
    print(f"chalkboard touchend patch applied ({f})")

    # Palm rejection: only allow Apple Pencil (stylus) on iPad; ignore finger/palm touches.
    # touch.touchType is iOS/iPadOS Safari-specific: 'stylus' = Apple Pencil, 'direct' = finger.
    # When undefined (non-iOS), the guard is skipped so desktop behaviour is unchanged.
    patched = patched.replace(
        "\t\t\t\tvar touch = evt.touches[ 0 ];\n\t\t\t\tmouseX = touch.pageX;",
        "\t\t\t\tvar touch = evt.touches[ 0 ];\n\t\t\t\tif ( touch.touchType !== undefined && touch.touchType !== 'stylus' ) { return; }\n\t\t\t\tmouseX = touch.pageX;",
        1,
    )
    print(f"chalkboard palm rejection patch applied ({f})")

    # Eraser button helper — shared toggle logic, defined once on window so both palettes
    # can reference it regardless of which initialises first.
    _eraser_toggle_fn = (
        "\t\t\tif ( !window._toggleEraserMode ) {\n"
        "\t\t\t\twindow._toggleEraserMode = function() {\n"
        "\t\t\t\t\twindow._chalkboardEraserMode = !window._chalkboardEraserMode;\n"
        "\t\t\t\t\tdocument.querySelectorAll( '.chalkboard-eraser-btn' ).forEach( function( b ) {\n"
        "\t\t\t\t\t\tb.classList.toggle( 'active', !!window._chalkboardEraserMode );\n"
        "\t\t\t\t\t\tb.setAttribute( 'aria-pressed', window._chalkboardEraserMode ? 'true' : 'false' );\n"
        "\t\t\t\t\t} );\n"
        "\t\t\t\t};\n"
        "\t\t\t}\n"
    )
    _eraser_button_html = (
        "\t\t\t\tvar eraserButton = document.createElement( 'li' );\n"
        "\t\t\t\teraserButton.classList.add( 'chalkboard-eraser-btn' );\n"
        "\t\t\t\teraserButton.innerHTML = '<i class=\"fa fa-eraser\"></i>';\n"
        "\t\t\t\teraserButton.setAttribute( 'role', 'button' );\n"
        "\t\t\t\teraserButton.setAttribute( 'aria-label', 'Toggle eraser mode' );\n"
        "\t\t\t\teraserButton.setAttribute( 'aria-pressed', 'false' );\n"
        "\t\t\t\teraserButton.addEventListener( 'click', window._toggleEraserMode );\n"
        "\t\t\t\teraserButton.addEventListener( 'touchstart', function( e ) { e.stopPropagation(); e.preventDefault(); window._toggleEraserMode(); } );\n"
        "\t\t\t\tpalette.querySelector( 'ul' ).appendChild( eraserButton );\n"
    )

    # Inject into mode-0 palette (boardmarkers — writing on slides).
    # Guard: original append line still present means not yet patched.
    _boardmarkers_original = (
        "\t\t\t\tvar palette = createPalette( boardmarkers, colorButtons );\n"
        "\t\t\t\tpalette.style.visibility = 'hidden'; // only show palette in drawing mode\n"
        "\t\t\t\tcontainer.appendChild( palette );"
    )
    if _boardmarkers_original in patched:
        patched = patched.replace(
            _boardmarkers_original,
            _eraser_toggle_fn
            + "\t\t\t\tvar palette = createPalette( boardmarkers, colorButtons );\n"
            "\t\t\t\tpalette.style.visibility = 'hidden'; // only show palette in drawing mode\n"
            + _eraser_button_html
            + "\t\t\t\tcontainer.appendChild( palette );",
            1,
        )
        print(f"notes-canvas eraser button patch applied ({f})")
    else:
        print(f"notes-canvas eraser button already present, skipping ({f})")

    # Inject into mode-1 palette (chalks — chalkboard view).
    _chalks_original = (
        "\t\t\t\tvar palette = createPalette( chalks, colorButtons );\n"
        "\t\t\t\tcontainer.appendChild( palette );"
    )
    if _chalks_original in patched:
        patched = patched.replace(
            _chalks_original,
            _eraser_toggle_fn
            + "\t\t\t\tvar palette = createPalette( chalks, colorButtons );\n"
            + _eraser_button_html
            + "\t\t\t\tcontainer.appendChild( palette );",
            1,
        )
        print(f"chalkboard eraser button patch applied ({f})")
    else:
        print(f"chalkboard eraser button already present, skipping ({f})")

    # Eraser mode touchstart: when window._chalkboardEraserMode is set, immediately erase
    # instead of draw (skipping the 500ms long-press timeout entirely).
    patched = patched.replace(
        "\t\t\t\tmouseX = touch.pageX;\n"
        "\t\t\t\tmouseY = touch.pageY;\n"
        "\t\t\t\tstartDrawing( ( mouseX - xOffset ) / scale, ( mouseY - yOffset ) / scale );\n"
        "\t\t\t\ttouchTimeout = setTimeout( startErasing, 500,  ( mouseX - xOffset ) / scale, ( mouseY - yOffset ) / scale );",
        "\t\t\t\tmouseX = touch.pageX;\n"
        "\t\t\t\tmouseY = touch.pageY;\n"
        "\t\t\t\tif ( window._chalkboardEraserMode ) {\n"
        "\t\t\t\t\tstartErasing( ( mouseX - xOffset ) / scale, ( mouseY - yOffset ) / scale );\n"
        "\t\t\t\t} else {\n"
        "\t\t\t\t\tstartDrawing( ( mouseX - xOffset ) / scale, ( mouseY - yOffset ) / scale );\n"
        "\t\t\t\t\ttouchTimeout = setTimeout( startErasing, 500,  ( mouseX - xOffset ) / scale, ( mouseY - yOffset ) / scale );\n"
        "\t\t\t\t}",
        1,
    )
    print(f"chalkboard eraser mode touchstart patch applied ({f})")

    f.write_text(patched)

# Append eraser button active-state CSS (guard against duplicate appends)
eraser_css = (
    "\n.chalkboard-eraser-btn { cursor: pointer; }\n"
    ".chalkboard-eraser-btn.active { outline: 2px solid white; border-radius: 3px; }\n"
)
for css_file in css_files:
    css = css_file.read_text()
    if "chalkboard-eraser-btn" not in css:
        css_file.write_text(css + eraser_css)
        print(f"chalkboard eraser button CSS patch applied ({css_file})")
    else:
        print(f"chalkboard eraser button CSS already present, skipping ({css_file})")
