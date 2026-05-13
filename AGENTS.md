# NeuroGolf Lab Agent Notes

- The active NeuroGolf Lab repo for evaluation work is on the Vast server at `/root/webgui`.
- Connect with `ssh -p 20347 root@96.3.252.118`.
- Use the browser tunnel convention `ssh -p 20347 root@96.3.252.118 -L 8080:localhost:8080` when local access to the server app is needed.
- The server currently runs the backend with `python3 -m uvicorn server:app --host 0.0.0.0 --port 8081` unless changed in the repo environment.
- Keep workflow evaluation notes in `WORKFLOW_EVAL.md` inside the active server repo.
- Do not print `.env` secret values, commit secrets, push to GitHub, or bypass the visual graph workflow except for backend diagnostic comparison.
