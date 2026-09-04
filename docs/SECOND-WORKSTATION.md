# Continue Asterion on a second workstation

This guide moves Asterion development to another Windows computer without treating copied build output or local chat state as project authority.

The Git repository is the source of truth. A local Codex project connects to a folder on the current computer, so the second workstation needs its own clean clone. Durable instructions live in this repository, especially `AGENTS.md` and the files under `docs/`.

Official Codex references:

- [Projects and chats](https://learn.chatgpt.com/docs/projects)
- [Local environments](https://learn.chatgpt.com/docs/environments/local-environment)
- [ChatGPT desktop app for Windows](https://learn.chatgpt.com/docs/windows/windows-app)

## 1. Finish work on the source workstation

Do not hand off an unknown or partially committed working tree.

```powershell
Set-Location <asterion-repository>
git status --short --branch
pnpm test
pnpm check
pnpm build
git push origin main
```

If work is intentionally incomplete, commit it to a dedicated feature branch and push that branch instead of mixing it into `main`.

## 2. Install the target workstation tools

Install and verify:

- ChatGPT desktop app with Codex access
- Git for Windows
- Node.js 22 or newer
- pnpm 11.19.0 through Corepack or an equivalent trusted installation
- Blender from the official Blender distribution
- Git LFS before the first large 3D source asset is committed

The official Windows app can be installed through Microsoft Store or with the command documented by OpenAI:

```powershell
winget install --id 9PLM9XGG6VKS -s msstore
```

Verify the development tools:

```powershell
git --version
node --version
pnpm --version
blender --version
git lfs version
```

If `blender` is not on `PATH`, record its absolute executable path in local tooling configuration. Do not hard-code a workstation-specific Blender path into tracked source files.

## 3. Clone instead of copying the working directory

Choose a data-drive path appropriate for the workstation:

```powershell
New-Item -ItemType Directory -Force D:\projects | Out-Null
Set-Location D:\projects
git clone https://github.com/Alvestrasza/Asterion.git asterion
Set-Location D:\projects\asterion
git switch main
git pull --ff-only
```

Install only reproducible dependencies:

```powershell
corepack enable
pnpm install --frozen-lockfile
pnpm test
pnpm check
pnpm build
```

Do not copy these directories from the first workstation:

- `node_modules/`
- `.next/`
- caches, logs, coverage output, or temporary release archives
- a manually copied `.git/` directory

They are generated, architecture-sensitive, or already represented by Git history.

## 4. Open the clone in Codex

1. Sign in to the ChatGPT desktop app with the intended account.
2. Select Codex.
3. Add `D:\projects\asterion` as a local project and make it the primary folder.
4. Keep the sandbox enabled and use targeted approvals for external access.
5. Start a new focused chat and ask it to read `AGENTS.md` plus `docs/PROJECT-STATUS.md` before changing files.

Chat transcripts may be available through the account, but they do not transfer a local working tree, ignored files, installed tools, or machine-specific credentials. Git plus the tracked project guidance is the durable handoff.

The Codex desktop app can generate local-environment setup and action configuration inside the repository's `.codex/` folder. Once generated and reviewed, it may be committed so both workstations share the same setup, test, and build actions. Do not invent or hand-edit an unverified format.

## 5. Handle private material separately

`.private/` and real environment files are deliberately excluded from Git.

For 3D-only work, do not transfer deployment SSH keys or production-like environment files. If the second workstation must deploy later:

1. Prefer a dedicated key scoped to that workstation and task.
2. Transfer it through an approved encrypted channel.
3. Restrict its filesystem permissions to the interactive user.
4. Verify the expected host key through an independent trusted record.
5. Keep the material under `.private/` and confirm `git status` does not list it.

Never send private files through GitHub issues, pull requests, chat messages, or repository attachments.

## 6. Prepare Git LFS for 3D assets

Enable LFS before committing the first large binary source file:

```powershell
git lfs install
git lfs track "*.blend"
git lfs track "*.glb"
git lfs track "*.fbx"
git add .gitattributes
git commit -m "chore: track 3D assets with Git LFS"
git push origin main
```

Review repository storage and bandwidth limits before adding high-resolution textures or many binary revisions. Prefer compact source assets and remove unused generated exports before committing.

## 7. Move work between both computers

At every handoff:

```powershell
git status --short --branch
git add <reviewed-files>
git commit -m "<focused English commit message>"
git push origin <branch>
```

On the receiving workstation:

```powershell
git status --short --branch
git pull --ff-only
```

Do not edit the same branch with uncommitted changes on both computers. Use feature branches or Codex worktrees for concurrent work.

## Acceptance checklist

- The clone has a clean working tree and the expected commit.
- `pnpm test`, `pnpm check`, and `pnpm build` pass locally.
- Blender starts and can export a minimal `.glb` test asset.
- `.private/`, `.env.local`, and credentials remain untracked.
- `AGENTS.md`, `docs/PROJECT-STATUS.md`, and `docs/3D-ASSET-PIPELINE.md` are readable from the new Codex project.
- No deployment is attempted until its access and target are revalidated from the second workstation.
