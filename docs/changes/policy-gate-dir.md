# Change record — policy/gate-dir

TYPE: policy
WHY: keep `.gate/` in the tree with its contents ignored, rather than adding the directory to the root
`.gitignore`, because `.gate/` is in the protected set and a result the gate writes belongs somewhere the
protected set already covers.

Split out of chore/audit-reports: the gate refused that change with `type FAIL` and `protected_files FAIL`
naming `.gate/.gitignore`, and this is the safe path it printed. The refusal was correct and I had not
noticed the file was protected.
