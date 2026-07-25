# Configuration Grammar

The rules file is YAML, named `rules.yaml` by default and kept at the root of
the dotfiles repository.  All relative `source` paths are resolved against the
directory containing the rules file, regardless of the working directory
dotfiler is invoked from.

The file has three top-level sections, all optional:

| section    | contents                                        |
|------------|-------------------------------------------------|
| `tasks`    | files and directories to install                |
| `packages` | system packages to install, per package manager |
| `config`   | application settings                            |

## Tasks

`tasks` is a list of task entries:

```yaml
tasks:
  - target: ~/.zshrc          # required
    source: zsh/zshrc         # required except for non-recursive remove
    action: symlink           # optional, default: symlink
    recurse: false            # optional, default: false
    exclude: ["*.tmp"]        # optional, recurse only
    mode: "0600"              # optional
    match: {os: debian}       # optional, absent match key means "always"
```

### Task Keys

- **`target`** (required): the path where the file or directory is installed
  (or, for `remove`, removed).  A leading `~` is expanded to the invoking
  user's home directory.  Missing parent directories are created
  automatically, except by `remove` tasks.

- **`source`**: the source path, relative to the rules file's directory
  (absolute paths are permitted but discouraged).  Required for every
  action except a non-recursive `remove`, which ignores it.

- **`action`**: what dotfiler does at the target.
    - `symlink` (default): target is a symbolic link to the source.  Links are
      written with the source's absolute path (matching the legacy script);
      they do not survive moving the repository, but rerunning dotfiler
      repairs them.
    - `hardlink`: target is a hard link to the source, for applications that
      refuse to follow symlinks.
    - `copy`: target is a byte-for-byte copy of the source.
    - `decrypt`: source is GPG ciphertext (conventionally with a `.gpg`
      suffix); the target is the decrypted plaintext.  Necessarily a copy,
      never a link.  Decryption uses the invoking user's GPG agent/private
      key.
    - `remove`: the target is removed instead of installed.  Removal is
      idempotent — an absent target is success, not an error.  A
      non-recursive remove deletes a file, a symlink (the link itself,
      never its destination), or an empty directory.  A non-empty directory
      target is an install-time error, not a conflict: `on_conflict` never
      applies to it, because no setting may delete a directory's contents.
      A target that is *dotfiler's own* — a symlink whose destination
      resolves inside the repository, or a file sharing an inode (same
      device and inode number) with a repository file, i.e. a hardlink —
      is removed silently; removing anything else is a *conflict*, handled
      per `config.on_conflict`.  See `recurse` for retiring a previously
      installed tree.

  Keys that are meaningless for a task's action are ignored, not errors
  (e.g. `source` and `mode` on a non-recursive `remove`, or `mode` on a
  `symlink`).

- **`recurse`**: when `true`, `source` must be a directory.  Its directory
    tree is recreated under `target`, and every file found beneath it is
    handled according to `action` — including `decrypt`, which then treats
    every file in the tree as ciphertext (a non-ciphertext file in such a tree
    is an install-time error).  When `false` (default), `source` is installed
    as a single filesystem entry (so a non-recursive `symlink` task whose
    source is a directory produces one symlink to that directory).

    With `action: remove`, `source` is required and defines what gets removed:
    the source tree is expanded exactly as for a recursive install (same
    ordering, `exclude`, and source-exclusion rules), but each corresponding
    target path is marked for removal instead.  Execution removes deepest
    first, and a directory is removed only when empty — deleting the last file
    in a directory therefore also deletes the directory, while directories
    still holding foreign files are silently left standing.  Removal only ever
    touches paths mirrored in the source tree, so the source tree must remain
    in the repository while the removal rule is active.

- **`exclude`**: recursive tasks only.  A list of glob patterns; matching
  paths are skipped by this task's expansion.  Needed only for files no task
  should install — anything claimed as another task's `source` is skipped
  automatically (see [Resolution and Precedence](#resolution-and-precedence)).
  A pattern containing no `/` is matched against basenames at any depth
  (`*.tmp` excludes `a.tmp` and `sub/dir/b.tmp`); a pattern containing `/` is
  matched against the whole path relative to `source` (`cache/*` excludes only
  the top-level cache directory's contents).  When a directory matches, its
  entire subtree is excluded.

- **`mode`**: octal permission string applied to the installed target.
  Meaningful for `copy`, `hardlink`, and `decrypt`; `decrypt` defaults to
  `0600` when `mode` is not given.  Ignored for `symlink` and `remove`.
  Note that a hard link shares its inode with the source, so `mode` on a
  `hardlink` task changes the repository file's permissions too.

- **`match`**: conditions restricting when the task applies; see
  [Match Rules](#match-rules).  A task with no `match` always applies.

### Resolution and Precedence

Before touching the filesystem, dotfiler resolves the matched tasks into a
flat map of *target path → action*, then executes each action exactly once.
Resolution proceeds in two passes:

1. Non-recursive tasks claim their target paths.
2. Recursive tasks expand their trees in order of declared `target` depth,
   deepest first, each filling only paths not already claimed.  So a path is
   skipped when a non-recursive task, or a recursive task with a deeper
   declared `target`, has already claimed it.

Remove tasks participate identically — a non-recursive remove claims its
target in pass 1, a recursive remove expands in pass 2 — and a matched
remove and a matched install claiming the same target is an
equal-specificity configuration error like any other.

During expansion, a recursive task also skips any path that another task —
recursive or not — names as its `source`; a directory source excludes its
whole subtree.  This applies whether or not the claiming task's `match`
rules hold on the current host: a file some task claims as a source has a
special purpose, and installing it raw on hosts where that task happens not
to match is almost never wanted (e.g. ciphertext must not be symlinked into
place just because gpg is absent).  Match-independence also keeps
resolution deterministic across hosts.

Consequences:

- A more specific task overrides a recursive task for a path inside its tree
  (e.g. a `decrypt` task for `~/.mutt/aliases` overrides the recursive
  symlink task for `~/.mutt`).  No target is ever installed twice in one run.
- An override that installs a source under a different name (decrypting
  `mutt/aliases.gpg` to `~/.mutt/aliases`) automatically suppresses the
  recursive install of the source at its own tree position
  (`~/.mutt/aliases.gpg`) — no `exclude` boilerplate.  In the rare case a
  source should *also* be installed at its tree position, add an explicit
  task for that target: explicit tasks are unaffected by source exclusion.
- Two *matched* tasks of equal specificity claiming the same target is a
  configuration error, reported before anything is installed.  To define
  host-dependent variants of one target, give the tasks complementary
  `match` rules so at most one matches on any host.

Execution is idempotent: the current state of each target is inspected and
only changed if it differs from the planned action.  A target that exists
but is the wrong kind of entry (a real file where a symlink belongs, a link
to the wrong place) is a *conflict*, handled per `config.on_conflict` and
CLI flags — replacement semantics are runtime behavior, not grammar.

## Match Rules

A `match` block is a mapping of rule names to values.  All rules in a block
are ANDed; the task or package entry applies only if every rule holds.

Every rule value takes one of three forms:

| form                        | meaning                          |
|-----------------------------|----------------------------------|
| scalar                      | equals                           |
| list                        | any-of (OR)                      |
| mapping `{not: <scalar or list>}` | none-of (negation)         |

```yaml
match:
  os: [debian, freebsd]   # os is debian OR freebsd
  domain:
    not: example.com      # AND domain is not example.com
```

### Rules

- **`os`**: matched against the host's *fact set*, a lowercase set of
    identifiers built from the kernel name and, on Linux, the `ID` field of
    `/etc/os-release`:

    | host    | fact set            |
    |---------|---------------------|
    | macOS   | `{darwin, macos}`   |
    | Debian  | `{linux, debian}`   |
    | Ubuntu  | `{linux, ubuntu}`   |
    | FreeBSD | `{freebsd}`         |

    Distro names match only themselves: `os: debian` does not match Ubuntu.
    There is no distro-family concept; group related distros by enumeration
    (`os: [debian, ubuntu]`), noting that a new derivative matches nothing
    until added to such lists.  The only built-in groupings are kernel facts
    (`os: linux` matches any Linux) and the `darwin`/`macos` synonym pair.

- **`domain`**: true if the host's FQDN equals the value or is a subdomain
  of it (`domain: example.com` matches `example.com` and
  `foo.example.com`, not `notexample.com`).  Comparison is
  case-insensitive.

- **`exists`**: boolean.  True if the task's `target` exists as any kind of
  filesystem entry, including a broken symlink (`lexists` semantics).
  `exists: false` with `action: copy` yields create-once behavior: the
  file is created when missing and never updated afterwards.  Only
  meaningful on tasks.

- **`executable`**: true if the named command is available.  A bare name is
  searched for in `PATH`; an absolute path must exist and be executable; a
  relative path is ambiguous, and therefore a configuration error.

## Packages

`packages` is a list of entries pairing an optional `match` block with one
or more package-manager keys, each holding a list of package names:

```yaml
packages:
  - match:
      os: darwin
    brew: [bat, git, mtr, wget]

  - match:
      os: debian
    apt: [bat, zsh, mtr]
    snap: [certbot]
```

Manager names are an enumerated vocabulary (initially `brew`, `apt`, `snap`,
`pkg`; extensible).  Any key in an entry other than `match` must be a known
manager — anything else is a configuration error.  One entry may carry
several managers.  Package installation is opt-in at runtime; the grammar
only carries the data.

## Config

```yaml
config:
  on_conflict: ask
```

- **`on_conflict`**: default handling when a target exists but is not what
  the task would install — or, for `remove`, is not dotfiler's own (the
  symlink-destination / shared-inode predicate defined under the `remove`
  action): `ask` (default, prompt per conflict), `replace`, or `skip`.
  CLI flags override per run.
