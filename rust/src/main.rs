fn parse_subcommands(text: &str) -> Vec<String> {
    println!("Input was: {}", text);
    Vec::new()
}



fn main() {
    const HELP_MSG: &str = r#"
usage: fts [-h] [-q | -v] [-log LOGFILE] COMMAND ...

FTS: File transfers! =)

positional arguments:
  COMMAND               available commands:
    open                start a server and listen for incoming transfers
    send                connect to the target server and transfer the file
    close               close a detached server
    trust               allow a new certificate to be trusted if changed
    alias               manage aliases
    cache               Manage cache and data inside ~/.fts
    plugins             Manage TUI plugins

options:
  -h, --help            show this help message and exit
  -q, --quiet           suppress non-critical output
  -v, --verbose         enable verbose debug output
  -log, --logfile LOGFILE
                        log output to a file
"#;

    parse_subcommands(HELP_MSG);
}