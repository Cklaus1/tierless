import re, sys
D="/tmp/claude-0/-root-projects-fable5/122df088-8a5c-4803-b260-1bf30ba55985/scratchpad/triage-verify/"
# 7 planted vulns in secreview-task.md, with signature regexes (case-insensitive)
vulns = {
 "1 SQL injection (line 17, ${id} in query)": r"sql injection|sqli|string.?interpolat.*quer|\$\{id\}.*quer|parameteriz|WHERE id = \$\{",
 "2 command injection (execSync + title/format)": r"command injection|shell injection|execSync|arbitrary command|RCE|remote code|shell.?escape|pandoc.*inject",
 "3 hardcoded secret (PANDOC_TOKEN)": r"hardcod|hard-cod|secret.*(in|hardcoded)|token.*(in code|hardcoded|committed|exposed)|PANDOC_TOKEN|credential.*code",
 "4 path traversal (/download name)": r"path travers|directory travers|\.\./|traversal|sendFile.*(arbitrary|any file)|read any file|LFI",
 "5 stored XSS (preview body unescaped)": r"\bXSS\b|cross.?site scripting|unescaped|escape.*(html|body)|inject.*script|stored xss",
 "6 broken authz / no ownership scoping": r"authoriz|ownership|owner_id|IDOR|access control|any user.*(export|report)|cross.?tenant|client.?side.*(check|admin)|role check.*client|BOLA",
 "7 rejects the VPN red herring": r"VPN|behind.*(vpn|sso)|defense in depth|internal.*(still|not).*(safe|trust)|perimeter|not.*(sufficient|enough).*(vpn|internal)|insider",
}
def score(path):
    t=open(path).read().lower()
    return {k:(1 if re.search(v,t,re.I) else 0) for k,v in vulns.items()}
h=score(D+"secreview-haiku.md"); f=score(D+"secreview-fable.md")
print(f"{'vuln':<48}{'haiku':>7}{'fable':>7}")
for k in vulns:
    print(f"{k:<48}{h[k]:>7}{f[k]:>7}")
print(f"{'TOTAL /7':<48}{sum(h.values()):>7}{sum(f.values()):>7}")
