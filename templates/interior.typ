// =============================================================================
// KDP interior — page geometry and front matter
// =============================================================================
//
// Compiled by scripts/build-interior.py, which passes every dimension in as
// sys.inputs. Nothing in this file needs editing when the trim or the extent
// moves; that is the whole reason the numbers arrive from outside.
//
//   trim_w, trim_h     trim size in inches
//   bleed              "true" if art runs to the page edge
//   margin_*           inside / outside / top / bottom, in inches, already
//                      cleared against KDP's minimum gutter for this extent
//   body               path to the manuscript body, relative to the project root
//   parity_leaf        "true" to append a blank leaf for an even page count
//   toc                "true" to generate a table of contents (default: true)
//
// EDIT THIS FILE FREELY. It is layout, not content. build-interior.py never
// rewrites it, so typography changes survive every rebuild. What must NOT go in
// here is the text of the book — that lives at [paths].body.
//
// ONE TYPST TRAP WORTH KNOWING. A literal slash-asterisk anywhere in this file
// opens a block comment and silently eats the rest of it. The document still
// compiles, just shorter. If a rebuild loses its back half for no reason, this
// is why.

#let to-in(key, fallback) = float(sys.inputs.at(key, default: fallback)) * 1in
#let flag(key) = sys.inputs.at(key, default: "false") == "true"

#let trim-w = to-in("trim_w", "6.0")
#let trim-h = to-in("trim_h", "9.0")
#let bleed-on = flag("bleed")
#let bleed = if bleed-on { 0.125in } else { 0pt }

#let m-inside = to-in("margin_inside", "0.75")
#let m-outside = to-in("margin_outside", "0.63")
#let m-top = to-in("margin_top", "0.68")
#let m-bottom = to-in("margin_bottom", "0.80")

#let body-path = sys.inputs.at("body", default: "manuscript/body.typ")
#let parity = flag("parity_leaf")
#let toc-on = sys.inputs.at("toc", default: "true") == "true"

// With bleed the FILE is larger than the trim, on the top, bottom and outer
// edges only. Never on the gutter edge — that edge is bound, not trimmed.
#let page-w = trim-w + bleed
#let page-h = trim-h + 2 * bleed

// --- Identity ----------------------------------------------------------------
//
// READ FROM book.toml, NEVER TYPED HERE. build-interior.py regenerates
// dist/book.json from the manifest on every build, so the title page and the
// cover cannot drift apart.
//
// Values arrive as data rather than as markup, so a title containing `#`, `$`,
// `*`, `_`, `@` or a backslash renders literally with no escaping needed.
#let ident = json(sys.inputs.at("book_json", default: "/dist/book.json"))

#let book-title = ident.title
#let book-author = ident.author

#set document(title: book-title, author: book-author)

// --- Page --------------------------------------------------------------------
//
// `binding: left` makes Typst read `inside` and `outside` as gutter-relative
// rather than as left and right, so the wide margin alternates onto the bound
// edge of each spread. Setting a plain `left`/`right` margin instead puts the
// gutter on the wrong side of every verso page — legal, and wrong on half the
// book.
#set page(
  width: page-w,
  height: page-h,
  binding: left,
  margin: (
    inside: m-inside + bleed,
    outside: m-outside + bleed,
    top: m-top + bleed,
    bottom: m-bottom + bleed,
  ),
  numbering: "1",
  number-align: center,
)

// --- Type --------------------------------------------------------------------
//
// A serif body face is the default because it sets more characters per line at
// the same optical size, which matters across hundreds of pages.
//
// Libertinus Serif ships with Typst, so this compiles on a machine with no fonts
// installed at all. Headings are differentiated by size and weight rather than by
// a second family, deliberately: Typst does NOT ship a matching sans, and naming
// a font that is not present is not an error — Typst substitutes silently and
// exits 0. Bundle a sans under [paths].fonts and name it here if you want one.
#set text(font: "Libertinus Serif", size: 10.5pt, lang: "en")
#set par(justify: true, leading: 0.62em, first-line-indent: 1.2em)

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  v(1.4in)
  text(size: 20pt, weight: "bold")[#it.body]
  v(0.5in)
}
#show heading.where(level: 2): it => {
  v(0.9em)
  text(size: 12.5pt, weight: "bold")[#it.body]
  v(0.25em)
}

// --- Front matter ------------------------------------------------------------

#page(numbering: none)[
  #v(2.6in)
  #align(center)[
    #text(size: 26pt, weight: "bold")[#book-title]
    #v(0.4in)
    #text(size: 13pt)[#book-author]
  ]
]

#pagebreak(to: "odd", weak: true)

// The outline is generated from real Typst headings in the manuscript. It is
// deliberately limited to levels 1 and 2: chapter/part headings and their
// immediate sections, not every small subsection. Turn it off in book.toml for
// books whose structure should not appear in a contents page.
#if toc-on {
  outline(title: [Contents], depth: 2)
  pagebreak(to: "odd", weak: true)
}

// --- Body --------------------------------------------------------------------
//
// SCOPE CAVEAT, and it bites everyone once. Typst evaluates an included file in
// its own module scope, so the body CANNOT see `#let` bindings defined above —
// a helper defined here is not callable from the body file.
//
// If the book needs shared helpers, do not fight this: have the build
// concatenate the preamble and the body into one file before compiling, which
// is what a generated book wants anyway. For ordinary prose, plain markup in
// the body file is all that is needed and `include` is fine.
#include "/" + body-path

// A blank leaf so the finished book has an even page count, which every printer
// requires. Whether it is needed is decided by build-interior.py, from a real
// measurement — Typst cannot decide it, because a conditional on
// counter(page).final() changes the very count it is reading and oscillates.
#if parity {
  pagebreak()
  page(numbering: none)[]
}
