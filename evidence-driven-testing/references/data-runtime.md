# Claude Code execution boundaries

Documentation reviewed 2026-11-05; these capabilities were not exercised here.
Check the installed client, OS, active settings and the project's actual tools
before relying on them. This reference supplies no configuration changes.

Claude Code's [Bash sandbox](https://code.claude.com/docs/en/sandboxing)
covers shell commands and their children. File tools, MCP servers and hooks
run outside it. Tool permissions and `allowed-tools` are separate from sandbox
isolation. Inspect any excluded command or unsandboxed retry route.

The same documentation describes credential masking through sentinel values
and proxy substitution, requiring TLS termination and allowed destinations.
It has trusted-settings and OS-specific constraints; a masked credential file
on macOS is blocked rather than substituted. This does not reduce the server
permissions of requests that still authenticate. Verify the deployed setup;
do not transplant these settings into Codex or assume masking is enabled.
