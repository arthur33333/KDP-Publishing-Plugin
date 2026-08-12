// =============================================================================
// KDP full-wrap cover — back cover, spine and front cover on one sheet
// =============================================================================
//
// Compiled by scripts/build-cover.py, which measures the finished interior and
// passes the geometry in. Nothing here needs editing when the extent moves.
//
//   pages        finished interior leaf count (even)
//   spine        spine width in inches, already computed from pages x caliper
//   trim_w       trim width in inches
//   trim_h       trim height in inches
//   spine_text   "true" if this spine is wide enough for KDP to print type on
//
// This file is layout. Edit the design freely — build-cover.py never rewrites
// it. What it must not do is override `page(width:)`; build-cover.py measures
// the rendered wrap afterwards and fails the build if the folds moved.
//
// THREE RULES THAT ARE NOT STYLE PREFERENCES
//
// 1. NOTHING ON THE FRONT PANEL IS ANCHORED UP FROM THE BOTTOM EDGE. The whole
//    panel is one fixed-height box with `v(1fr)` spacers. Anchoring a block to
//    the foot makes its position a guess about how tall everything above it
//    turned out, and that guess is wrong the moment the title or subtitle wraps
//    to another line. With `1fr` a longer subtitle squeezes the gaps instead of
//    overprinting the byline — the collision cannot happen rather than being
//    tuned away.
//
// 2. NEITHER BOTTOM CORNER OF THE BACK PANEL CARRIES TYPE. KDP places the
//    retailer barcode in one and other channels use the other, so neither is
//    safe whichever channel this wrap is built for.
//
// 3. A LITERAL SLASH-ASTERISK ANYWHERE IN THIS FILE opens a Typst block comment
//    and silently eats the rest of it. Write URLs containing one as a
//    concatenation.

#let pages = int(sys.inputs.at("pages", default: "200"))
#let spine = float(sys.inputs.at("spine", default: "0.5")) * 1in
#let trim-w = float(sys.inputs.at("trim_w", default: "6.0")) * 1in
#let trim-h = float(sys.inputs.at("trim_h", default: "9.0")) * 1in
#let has-spine-text = sys.inputs.at("spine_text", default: "true") == "true"

#let bleed = 0.125in

// KDP's stated minimum is 0.25in from the trim line. 0.375in is used here
// because type sitting exactly on the compliance figure reads on a printed
// proof as though it is about to fall off the page. Lower it to 0.25in if the
// design needs the room; do not go under.
#let safe = 0.375in

#let wrap-w = bleed + trim-w + spine + trim-w + bleed
#let wrap-h = bleed + trim-h + bleed

// Fold lines, measured from the LEFT edge of the wrap. The back cover is on the
// left, the front on the right — that is the order a wrap is laid out flat.
#let fold-1 = bleed + trim-w
#let fold-2 = fold-1 + spine

#let front-x = fold-2 + safe
#let back-x = bleed + safe
#let live-w = trim-w - 2 * safe

// --- Identity ----------------------------------------------------------------
//
// READ FROM book.toml, NEVER TYPED HERE. build-cover.py regenerates
// dist/book.json from the manifest on every build, so the cover, the title page
// and the KDP listing all derive from one string and cannot disagree. KDP takes
// the title exactly as the cover prints it and locks the field 72 hours after
// publication, so a cover that says something slightly different from the
// listing is a mistake that cannot be corrected later.
//
// Values arrive as data rather than as markup, so a title containing `#`, `$`,
// `*`, `_`, `@` or a backslash renders literally with no escaping needed.
#let ident = json(sys.inputs.at("book_json", default: "/dist/book.json"))

#let title-lines = ident.title_lines
#let subtitle = ident.subtitle
#let author = ident.author
#let blurb = ident.blurb

// --- Palette -----------------------------------------------------------------
#let ground = rgb("#0f172a")
#let accent = rgb("#6366f1")
#let bright = rgb("#22d3ee")
#let paper = rgb("#f1f5f9")
#let muted = rgb("#94a3b8")

// Libertinus Serif ships with Typst, so this compiles on a machine with no fonts
// installed at all. Swap it for anything bundled under [paths].fonts — but
// whatever you name here must actually exist, because Typst substitutes silently
// and exits 0 when it does not.
#set document(title: ident.title + " — cover", author: author)
#set text(font: "Libertinus Serif", fill: paper)
#set page(width: wrap-w, height: wrap-h, margin: 0pt, fill: ground)

// --- Front panel -------------------------------------------------------------
// One fixed-height box. See rule 1 above before adding anything to it.
#place(top + left, dx: front-x, dy: bleed + safe)[
  #box(width: live-w, height: trim-h - 2 * safe)[
    #set par(leading: 0.28em)
    #text(size: 34pt, weight: "bold", fill: paper)[
      #title-lines.join("\n")
    ]

    #v(0.22in)
    #line(length: 2.0in, stroke: 2pt + accent)
    #v(0.20in)

    #if subtitle != "" {
      box(width: live-w - 0.2in)[
        #set par(leading: 0.55em)
        #text(size: 13pt, fill: muted)[#subtitle]
      ]
    }

    // Everything below stays IN THIS FLOW. Two blocks laid out from opposite
    // edges collide the moment anything between them gains a line.
    #v(1fr)

    #text(size: 14pt, weight: "medium")[#author]

    // Optical clearance only. The `1fr` above pushes the byline to the foot of
    // the box, which is the safe line exactly — legal, but it reads tight on a
    // printed proof. `safe` is the compliance figure and stays where it is.
    #v(0.14in)
  ]
]

// --- Spine -------------------------------------------------------------------
// KDP trims with variance toward either face, so type filling the spine's full
// width runs onto a cover. build-cover.py has already decided whether type is
// allowed here at all; this only caps it to the band that survives the trim.
#let spine-clear = 0.0625in
#let spine-band = spine - 2 * spine-clear

#if has-spine-text and spine-band >= 0.14in {
  place(top + left, dx: fold-1, dy: 0pt)[
    #box(width: spine, height: wrap-h)[
      #align(center + horizon)[
        #box(width: spine-band)[
          #align(center)[
            #rotate(90deg, reflow: false)[
              #box(width: wrap-h - 1.6in)[
                #align(center)[
                  #text(size: 10pt, weight: "bold")[#title-lines.join(" ")]
                  #h(0.25in)
                  #text(size: 9pt, fill: muted)[#author]
                ]
              ]
            ]
          ]
        ]
      ]
    ]
  ]
}

// --- Back panel --------------------------------------------------------------
// Type starts at the head and stops well clear of both bottom corners. See
// rule 2 above.
#place(top + left, dx: back-x, dy: bleed + 1.0in)[
  #box(width: live-w - 0.18in, height: trim-h - 2.6in)[
    #set par(justify: false, leading: 0.62em, spacing: 0.85em)
    #set text(size: 10.5pt, fill: rgb("#e2e8f0"))
    #blurb
  ]
]
