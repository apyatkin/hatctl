# Global DevOps Skills for Claude Code

## Overview

A set of 12 Claude Code skills covering common DevOps tools (GitLab, GitHub, Favro, Jira, K8s, Helm, Terraform, Ansible, Nomad, Vault, Consul, Docker). Skills are stored globally at `~/projects/.claude/skills/` so they're available when working in any company's repos. Each skill reads the active company's `ctx` config for company-specific connection details.

## Directory Structure

```
~/projects/
  CLAUDE.md                        # makes skills discoverable
  .claude/
    skills/
      gitlab/SKILL.md
      github/SKILL.md
      favro/SKILL.md
      jira/SKILL.md
      kubernetes/SKILL.md
      helm/SKILL.md
      terraform/SKILL.md
      ansible/SKILL.md
      nomad/SKILL.md
      vault/SKILL.md
      consul/SKILL.md
      docker/SKILL.md
  acme/
    repos/...
  globex/
    repos/...
```

### Discovery

`~/projects/CLAUDE.md`:

```markdown
# Projects

Skills in `.claude/skills/` are available for all company work.
Active company config is at `~/.config/ctx/companies/<name>/config.yaml`.
```

Claude Code walks up the directory tree from any repo under `~/projects/` and finds this CLAUDE.md, discovering the skills.

### Source of Truth

Skill files are authored in the `personal-tools` repo at `skills/<tool>/SKILL.md`. Deployed to `~/projects/.claude/skills/` via `ctx skills deploy` (symlinks from repo to target).

## Skill Template

Every skill follows this structure:

```markdown
---
name: <tool>
description: Use when working with <tool> — <trigger description>
---

# <Tool>

## Company Context

To get company-specific settings for <tool>:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use the relevant config section (documented per skill below)

If no company is active, ask the user which company context to use.

## Commands

<command reference>

## Runbooks

### <Workflow Name>
<step-by-step procedure>
```

The "Company Context" section is consistent across all skills. The config section each skill reads is specified below.

## Skill Specifications

### gitlab

**Triggers:** working with GitLab, MRs, CI pipelines, `glab` commands, GitLab API
**Config section:** `git.sources[]` where `provider: gitlab` — reads `host`, `group`, `token_ref`

**Commands:**
- `glab mr list`, `glab mr create`, `glab mr view`, `glab mr merge --squash`
- `glab ci status`, `glab ci view`, `glab ci trace`
- `glab repo clone`, `glab issue list`, `glab issue create`
- API: `curl -H "PRIVATE-TOKEN: $TOKEN" https://<host>/api/v4/...`

**Runbooks:**
- Debug failing CI pipeline — check `glab ci trace <job-id>`, read logs, identify failure
- Review MR — fetch diff, check CI status, review changes, approve
- Force-push recovery — use reflog to find lost commits

---

### github

**Triggers:** working with GitHub, PRs, Actions, `gh` commands
**Config section:** `git.sources[]` where `provider: github` — reads `org`, `token_ref`

**Commands:**
- `gh pr list`, `gh pr create`, `gh pr view`, `gh pr merge --squash`
- `gh run list`, `gh run view --log`, `gh run rerun`
- `gh issue list`, `gh issue create`, `gh release list`
- `gh api repos/<owner>/<repo>/...`

**Runbooks:**
- Debug failing workflow — `gh run view <id> --log`, find failed step, read logs
- Review PR — `gh pr diff`, `gh pr checks`, review and approve
- Create release — tag, create release, attach artifacts

---

### favro

**Triggers:** working with Favro, cards, boards, task tracking in Favro
**Config section:** `apps.favro` (new optional section) — reads `organization_id`, `email`, `token_ref`

**Commands:**
- List cards: `curl -u <email>:<token> -H "organizationId: <org>" https://favro.com/api/v1/cards?collectionId=<id>`
- Update card: `curl -X PUT` with `columnId` to move between states
- Add comment: `curl -X POST` to `/cards/<id>/comments`
- List collections: `curl` to `/collections`

**Runbooks:**
- List cards in a collection — fetch collection ID, list cards with status
- Move card to done — find card by name, get target column ID, update
- Add comment with work summary — format comment, POST to card

---

### jira

**Triggers:** working with Jira, issues, sprints, `jira` CLI
**Config section:** `apps.jira` (new optional section) — reads `host`, `project`, `email`, `token_ref`

**Commands:**
- `jira issue list -q "project=<KEY> AND sprint in openSprints()"`
- `jira issue view <KEY>-123`
- `jira issue create -t Task -s "title" -b "description"`
- `jira issue move <KEY>-123 "In Progress"`
- `jira issue comment add <KEY>-123 "comment"`

**Runbooks:**
- Create task from plan — extract title, description, acceptance criteria, create issue
- Triage bug — check for duplicates, set priority, assign, add to sprint
- Sprint close — list incomplete issues, move to next sprint or backlog

---

### kubernetes

**Triggers:** working with K8s, pods, deployments, `kubectl` commands, cluster debugging
**Config section:** `cloud.kubernetes` — reads `kubeconfig`, `refresh.provider`, `refresh.cluster`

**Commands:**
- `kubectl get pods -n <ns>`, `kubectl describe pod <pod> -n <ns>`
- `kubectl logs -f <pod> -n <ns> -c <container>`
- `kubectl exec -it <pod> -n <ns> -- /bin/sh`
- `kubectl rollout status deployment/<name> -n <ns>`
- `kubectl rollout undo deployment/<name> -n <ns>`
- `kubectl top pods -n <ns>`, `kubectl top nodes`
- `kubectl get events -n <ns> --sort-by=.lastTimestamp`

**Runbooks:**
- Debug CrashLoopBackOff — describe pod, check events, read previous logs (`--previous`), check resource limits
- Investigate OOM kill — check `kubectl describe` for `OOMKilled`, review resource requests/limits, check `kubectl top`
- Drain node safely — cordon, drain with `--ignore-daemonsets --delete-emptydir-data`, verify pods rescheduled
- View logs across pods — `kubectl logs -l app=<name> -n <ns> --prefix`

---

### helm

**Triggers:** working with Helm, chart releases, values files
**Config section:** `cloud.kubernetes` (same cluster context)

**Commands:**
- `helm list -n <ns>`, `helm status <release> -n <ns>`
- `helm template <chart> . -f values.yaml` (render locally)
- `helm diff upgrade <release> . -f values.yaml -n <ns>` (diff before apply)
- `helm upgrade --install <release> . -f values.yaml -n <ns>`
- `helm rollback <release> <revision> -n <ns>`
- `helm history <release> -n <ns>`

**Runbooks:**
- Diff before upgrade — always `helm diff upgrade` first, review changes, then apply
- Rollback release — `helm history` to find good revision, `helm rollback`, verify pods
- Template locally — `helm template` to inspect rendered manifests without applying

---

### terraform

**Triggers:** working with Terraform, OpenTofu, `tofu`/`terraform` commands, infrastructure as code
**Config section:** `cloud.terraform` — reads `vars` for `TF_VAR_*` env vars

**Commands:**
- `tofu init -backend=false` (safe local init)
- `tofu fmt`, `tofu validate`, `tflint`
- `tofu plan -out=/tmp/plan.tfplan`
- `tofu apply /tmp/plan.tfplan` (only when explicitly instructed)
- `tofu state list`, `tofu state show <resource>`
- `terragrunt plan`, `terragrunt run-all plan`

**Runbooks:**
- Plan safely — init, validate, plan to file, review output, only apply when instructed
- Import existing resource — `tofu import <resource> <id>`, plan to verify no diff
- Fix state drift — `tofu plan` to see drift, decide: apply to match config, or update config to match reality
- Move state — `tofu state mv <old> <new>` for refactors

**Safety:** Never run `tofu apply`, `tofu destroy`, `tofu state rm`, or `tofu import` without explicit user instruction.

---

### ansible

**Triggers:** working with Ansible, playbooks, inventory, ansible-vault
**Config section:** `ssh` — reads `keys` for SSH access; company config may include ansible-specific inventory paths

**Commands:**
- `ansible-playbook -u <user> -i inventory/<file> <playbook>.yaml`
- `ansible-playbook --vault-password-file .ansible_vault_pass <playbook>.yaml`
- `ansible-lint --profile min`
- `ansible-playbook --check --diff <playbook>.yaml` (dry run)
- `ansible-vault encrypt/decrypt/view <file>`

**Runbooks:**
- Run with vault — ensure vault password file exists, run playbook with `--vault-password-file`
- Limit to specific hosts — use `-l <host-pattern>` to target subset
- Dry-run — `--check --diff` to preview changes without applying
- Debug connection — `-vvv` for verbose SSH debug output

---

### nomad

**Triggers:** working with Nomad, jobs, allocations, deployments
**Config section:** `cloud.nomad` — reads `addr`, `token_ref`, `cacert`

**Commands:**
- `nomad status`, `nomad status <job>`
- `nomad alloc status <alloc-id>`, `nomad alloc logs <alloc-id>`
- `nomad alloc logs -f -stderr <alloc-id>`
- `nomad job plan <job.nomad.hcl>` (dry-run)
- `nomad job run <job.nomad.hcl>` (only when instructed)
- `nomad node status`, `nomad operator raft list-peers`

**Runbooks:**
- Debug failed allocation — `nomad alloc status` to see events, check resource exhaustion, read logs
- Rolling deploy — `nomad job plan` first, review diff, `nomad job run` when instructed
- Drain node — `nomad node drain -enable <node-id>`, monitor allocations rescheduling
- Read allocation logs — `nomad alloc logs -f -stderr <alloc-id>` for live debugging

**Safety:** Never run `nomad job run`, `nomad job stop`, or `nomad system gc` without explicit instruction.

---

### vault

**Triggers:** working with HashiCorp Vault, secrets, auth, policies
**Config section:** `cloud.vault` — reads `addr`, `auth_method`, `token_ref`

**Commands:**
- `vault status`, `vault token lookup`
- `vault secrets list`, `vault kv list secret/<path>`
- `vault kv get secret/<path>/<key>`
- `vault kv put secret/<path>/<key> foo=bar` (only when instructed)
- `vault kv metadata get secret/<path>/<key>`
- `vault policy list`, `vault policy read <policy>`
- `vault audit list`

**Runbooks:**
- Read secrets safely — `vault kv get` with `-format=json` for parsing
- Rotate token — check current token TTL with `vault token lookup`, renew or re-authenticate
- Check seal status — `vault status` to verify unsealed and HA mode
- Audit trail — `vault audit list` to verify audit logging is enabled

**Safety:** Never write, delete, or modify secrets/policies without explicit instruction.

---

### consul

**Triggers:** working with Consul, service mesh, KV store, health checks
**Config section:** `cloud.consul` — reads `addr`, `token_ref`

**Commands:**
- `consul members`, `consul catalog services`, `consul catalog nodes`
- `consul kv get <key>`, `consul kv get -recurse <prefix>/`
- `consul kv put <key> <value>` (only when instructed)
- `consul intention list`
- `consul operator raft list-peers`
- `consul monitor -log-level=debug`

**Runbooks:**
- List services and health — `consul catalog services`, then `consul health checks <service>`
- Read KV tree — `consul kv get -recurse <prefix>/` to dump all keys under a path
- Check cluster health — `consul operator raft list-peers`, verify leader exists and all peers healthy
- Debug service DNS — `dig @127.0.0.1 -p 8600 <service>.service.consul` to test Consul DNS

**Safety:** Never run `consul kv delete`, `consul leave`, or `consul force-leave` without explicit instruction.

---

### docker

**Triggers:** working with Docker, containers, compose, building images
**Config section:** `docker.registries` — reads `host`, `username_ref`, `password_ref`

**Commands:**
- `docker compose up --build`, `docker compose up -d`
- `docker compose logs -f <service>`, `docker compose down`
- `docker build -t <tag> .`, `docker push <tag>`
- `docker exec -it <container> /bin/sh`
- `docker ps`, `docker logs -f <container>`
- `docker system prune -a` (only when instructed)

**Runbooks:**
- Debug container — `docker logs <container>`, `docker exec` to inspect, `docker inspect` for config
- Rebuild from scratch — `docker compose down`, `docker compose build --no-cache`, `docker compose up`
- Clean up — `docker system df` to check usage, `docker system prune` when instructed
- Registry auth — `docker login <host>` using credentials from ctx config

## Deployment

### `ctx skills deploy` command

New CLI command that creates `~/projects/.claude/skills/` and symlinks each skill from the personal-tools repo:

```
ctx skills deploy
```

Behavior:
1. Reads skill source directory from the personal-tools repo (configured once in `~/.config/ctx/config.yaml` or auto-detected)
2. Creates `~/projects/.claude/skills/` if it doesn't exist
3. Creates `~/projects/CLAUDE.md` if it doesn't exist
4. For each skill directory in `skills/`, creates a symlink: `~/projects/.claude/skills/<tool>` -> `<repo>/skills/<tool>`
5. Reports which skills were linked

### Config for deploy source

`~/.config/ctx/config.yaml` (new global config file, not per-company):

```yaml
skills_source: /Users/alex/work/personal-tools/personal-tools/skills
```

## New ctx Config Sections

The Favro and Jira skills require new optional sections in company config that don't exist in the current ctx spec:

```yaml
apps:
  favro:
    organization_id: "org-123"
    email: "alex@acme.com"
    token_ref: keychain:acme-favro-token
  jira:
    host: "acme.atlassian.net"
    project: "INFRA"
    email: "alex@acme.com"
    token_ref: keychain:acme-jira-token
  slack:
    workspace: acme-corp
```

These extend the existing `apps` section. No code changes needed in ctx modules — skills read the YAML directly.

## Adding Custom Runbooks

Users add runbooks by editing the SKILL.md files directly. Since the deployed skills are symlinks back to the repo, edits are automatically tracked in git. Add new `### Runbook Name` sections under `## Runbooks` in any skill.
