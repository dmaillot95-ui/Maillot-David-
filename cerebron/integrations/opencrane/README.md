# CEREBRON Ω — OpenCrane integration

OpenCrane is integrated as an optional MCP/RAG documentation and knowledge service, not as compute capacity by itself.

Primary uses inside CEREBRON:
- expose curated documentation through MCP;
- build searchable documentation bundles from Git repositories;
- provide retrieval context to CEREBRON workers;
- keep documentation provenance explicit;
- support local or HTTP MCP transport.

Zero-euro rules:
- no paid fallback;
- no automatic provisioning of paid infrastructure;
- secrets are environment-only;
- OpenCrane does not count as a real worker unless an actual execution backend is separately verified;
- any external embedding/model endpoint must independently satisfy the zero-euro policy before activation.

Suggested environment variables:
- `CEREBRON_OPENCRANE_ENABLE=0`
- `CEREBRON_OPENCRANE_URL`
- `CEREBRON_OPENCRANE_ACCESS_TOKEN`

Recommended deployment modes:
1. local/CI MCP over stdio for repository documentation tasks;
2. HTTP MCP only behind HTTPS and authentication;
3. containerized deployment when a free compatible host is available.

Activation gate:
1. OpenCrane install succeeds;
2. documentation source is allowlisted;
3. indexing succeeds;
4. MCP endpoint responds;
5. authentication is verified for HTTP mode;
6. one retrieval test returns source provenance;
7. spend remains exactly 0 EUR.

State remains PREPARED until these checks are proven by an executed test.
