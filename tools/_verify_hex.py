import pathlib
import re

t = pathlib.Path(__file__).with_name("seed_mdp_hex.sql").read_text(encoding="utf-8")
hexs = re.findall(r"decode\('([0-9a-f]+)',\s*'hex'\)", t)
s = bytes.fromhex(hexs[0]).decode("utf-8")
idx = s.find("23")
out = pathlib.Path(__file__).with_name("_verify_out.txt")
out.write_text(repr(s[idx : idx + 30]), encoding="utf-8")
