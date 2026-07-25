# dotfiler

This application is useful for maintaining dotfiles and other data in your
home directory that you want to maintain from another source, such as a git
repository.

It uses a configuration grammar to determine how each file should be
reproduced.

Intended Features:
- symlinking or hard-linking of files to the repository version
- copying of files from the repository to the homedir destination
- creation of all necessary directories
- remove obsolete files
- "create but don't modify" ruleset
- "match" rules, restricting the conditions for when a file should be acted on
- support encrypted at rest files (encrypted version in repository decrypted
  for install)

