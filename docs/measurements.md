# What the numbers mean

Logical bytes are regular-file st_size totals in the inspected categories. Sparse files can have large logical sizes with few allocated blocks. Allocated bytes use st_blocks*512 where available; Windows may report unavailable. APFS clones, compression and shared extents mean block sums do not establish unique physical storage. Directory blocks and data outside the supported categories are excluded.

Hardlinks are counted once across the entire scan. Their bytes belong to whichever category is visited first. Symlinks, reparse points and special files are skipped. Missing means the category/root was not present, not inaccessible. Partial means a read failed or a traversal depth/time/entry budget stopped observation. Overall counts then describe a lower bound of the supported data, not a complete footprint. An empty complete category is different from unavailable allocation metrics.

The default traversal visits at most 100000 entries and checks a 10-second deadline. Process inspection has a 3-second timeout; Git queries have 5 seconds total. Individual filesystem calls can block beyond a deadline. The CLI provides no hard real-time guarantee. Max directory depth 64 also prevents pathological recursion.

Selected process RSS is resident memory per exact-name process, summed without deduplicating shared pages. It excludes many helpers and generic runtimes. ps-reported CPU has the OS command's measurement window, not a controlled benchmark interval. No memory leak, orphan, idle status or safe-to-stop judgment is inferred.

Worktree registration counts include main checkouts and may include stale registrations. They do not prove agent ownership, important work, current activity or whether a branch has been merged. Explicit project checks neither inspect tracked contents nor run status/fetch.

A meaningful performance comparison needs the same tool versions, workload, scan scope and machine conditions. Observed bytes are not bytes saved. This utility does not improve performance by itself; it makes a later decision better informed.
