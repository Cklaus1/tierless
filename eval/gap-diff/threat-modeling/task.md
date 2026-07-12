# Threat model

You're designing a **file-sharing feature** for a B2B SaaS app: a user uploads a file, gets a
shareable link, and recipients (who may not have accounts) can download it via the link. Files are
stored in cloud object storage (S3). Links can optionally be password-protected and can expire.

Produce a threat model: enumerate the assets worth protecting, the realistic attackers, and the
specific threats/attack surfaces this design introduces — with, for each threat, what could go
wrong and the mitigation. Be thorough; cover the trust boundaries.
