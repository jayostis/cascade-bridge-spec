# tests — Agent Context

- **A top-level test class is a heading of the tests page, listed in `spec.json`;** its nested classes are the
  situations and its methods the leaves. A docstring's first paragraph is the title where the name cannot spell it
  (the name itself with the letters a Python name cannot hold), and the paragraphs after it are the description. A name
  that can spell the title has no docstring.
- **The suite runs in random order.** A test builds what it asserts on and changes nothing another test reads. A run
  prints its seed; pass it back with `-p randomly --randomly-seed=N`.
