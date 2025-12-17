import re


def flatten_set(text, indent="    "):
    """
    Flatten a '{ ... }' set into a list of lines, one per argument.

    Args:
        text (str): The input multiline string defining the set.
        indent (str): The indentation to use for each line.

    Returns:
        str: Flattened list with each argument on its own line.
    """
    # Extract the contents inside the braces
    match = re.search(r'\{(.*)\}', text, re.DOTALL)
    if not match:
        return text  # no braces found, return original

    content = match.group(1)

    # Split by | and remove whitespace/newlines
    items = [item.strip() for item in content.split('|') if item.strip()]

    # Reconstruct as an indented list
    flattened = "\n".join(f"{indent}{item}" for item in items).replace("{", "\n\t")
    return flattened


# Example usage:
object_lines = """
Usage: ip [ OPTIONS ] OBJECT { COMMAND | help }
       ip [ -force ] -batch filename
where  OBJECT := { address | addrlabel | fou | help | ila | ioam | l2tp | link |
                   macsec | maddress | monitor | mptcp | mroute | mrule |
                   neighbor | neighbour | netconf | netns | nexthop | ntable |
                   ntbl | route | rule | sr | stats | tap | tcpmetrics |
                   token | tunnel | tuntap | vrf | xfrm }
       OPTIONS := { -V[ersion] | -s[tatistics] | -d[etails] | -r[esolve] |
                    -h[uman-readable] | -iec | -j[son] | -p[retty] |
                    -f[amily] { inet | inet6 | mpls | bridge | link } |
                    -4 | -6 | -M | -B | -0 |
                    -l[oops] { maximum-addr-flush-attempts } | -echo | -br[ief] |
                    -o[neline] | -t[imestamp] | -ts[hort] | -b[atch] [filename] |
                    -rc[vbuf] [size] | -n[etns] name | -N[umeric] | -a[ll] |
                    -c[olor]}

"""

print("Flattened OBJECT:")
print(flatten_set(object_lines))
