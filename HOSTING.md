# Hosting Clone to Confidence

This guide describes the safe hosted demo. It does not claim that the project is
already deployed; connecting a hosting account and creating the service remain
manual steps.

## Container smoke test

Build and run the included deployment image:

```bash
docker build -t clone-to-confidence .
docker run --rm -p 8080:8080 clone-to-confidence
```

The image starts `clone-to-confidence web --host 0.0.0.0 --public-demo` and uses
`PORT=8080` by default. Check the deployment health endpoint:

```bash
curl http://127.0.0.1:8080/api/health
```

Expected fields include `status: "ok"`, `mode: "public-demo"`,
`demoAvailable: true`, and `readOnly: true`.

## Render web service

Render is a practical low-configuration option for this repository because it
can build the existing Dockerfile directly from GitHub.

1. Push the repository to GitHub from your own account.
2. In Render, create a **Web Service** and select the repository.
3. Choose **Docker** as the runtime and keep the repository root as the build
   context.
4. Set the health check path to `/api/health`.
5. Deploy. The container reads the platform-provided `PORT` and remains in
   `--public-demo` read-only mode.
6. Open the generated URL and click **Run demo audit**.

No API key, database, Docker socket, or secret environment variable is needed.
Render account access, repository connection, billing choice, and the final
deploy action must be performed by the project owner.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8765` locally / `8080` in the image | HTTP listen port; explicit `--port` wins |
| `--host` | `127.0.0.1` | Keep the local default loopback-only; hosting uses `0.0.0.0` |
| `--public-demo` | off | Expose only the bundled read-only demo |

## Logs and limitations

The process prints its bound URL on startup. HTTP request logging is intentionally
quiet to avoid putting repository paths in logs. The health endpoint is suitable
for platform smoke checks, but it does not prove that Docker or a user's project
works. Public mode does not accept filesystem paths, ZIP uploads, Git URLs,
verification commands, or fix applications. A future remote-audit feature needs
an isolated worker and strict archive/network policies before it should be made
public.
