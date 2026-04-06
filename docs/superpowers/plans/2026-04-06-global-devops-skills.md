# Global DevOps Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create 12 Claude Code DevOps skills stored at `~/projects/.claude/skills/`, add `ctx skills deploy` command, and create `~/projects/CLAUDE.md` for skill discovery.

**Architecture:** Each skill is a `SKILL.md` file with YAML frontmatter (name, description) and structured sections (Company Context, Commands, Runbooks). Skills are authored in the `personal-tools` repo under `skills/<tool>/SKILL.md` and symlinked to `~/projects/.claude/skills/` via `ctx skills deploy`. A shared company-context preamble teaches each skill how to read the active ctx config.

**Tech Stack:** Markdown (SKILL.md files), Python/Click (ctx skills deploy command), pytest (testing)

---

### Task 1: GitLab Skill

**Files:**
- Create: `skills/gitlab/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: gitlab
description: Use when working with GitLab — MRs, CI pipelines, glab CLI, GitLab API, or any GitLab-related task
---

# GitLab

## Company Context

To get company-specific GitLab settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Find entries in `git.sources` where `provider: gitlab` — use `host`, `group`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Merge Requests

```bash
glab mr list                              # list open MRs
glab mr create --title "title" --description "desc"  # create MR
glab mr view <number>                     # view MR details
glab mr merge <number> --squash           # merge with squash
glab mr approve <number>                  # approve MR
glab mr diff <number>                     # view diff
```

### CI/CD

```bash
glab ci status                            # current pipeline status
glab ci view <pipeline-id>               # pipeline detail
glab ci trace <job-id>                    # stream job logs
glab ci retry <job-id>                    # retry failed job
```

### Issues

```bash
glab issue list                           # list issues
glab issue create --title "title"         # create issue
glab issue view <number>                  # view issue
```

### API (when glab doesn't cover it)

```bash
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/groups/<group>/projects?include_subgroups=true"
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/projects/<id>/pipelines"
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/projects/<id>/merge_requests?state=opened"
```

## Runbooks

### Debug Failing CI Pipeline

1. Check pipeline status: `glab ci status`
2. Find the failed job: `glab ci view <pipeline-id>`
3. Read job logs: `glab ci trace <job-id>`
4. Look for the error message in the logs
5. If it's a flaky test or transient error: `glab ci retry <job-id>`
6. If it's a real failure: fix locally, push, verify new pipeline

### Review a Merge Request

1. View the MR: `glab mr view <number>`
2. Check CI status: `glab ci status`
3. Review the diff: `glab mr diff <number>`
4. If changes look good and CI passes: `glab mr approve <number>`
5. Merge when ready: `glab mr merge <number> --squash`

### Recover from Force-Push

1. Check reflog on the remote branch: `git reflog show origin/<branch>`
2. Find the commit before the force-push
3. Reset to that commit: `git reset --hard <sha>`
4. Force-push the recovery: `git push --force-with-lease origin <branch>`
```

- [ ] **Step 2: Verify the file exists and has correct frontmatter**

Run: `head -3 skills/gitlab/SKILL.md`
Expected: `---`, `name: gitlab`, `description: Use when working with GitLab`

- [ ] **Step 3: Commit**

```bash
git add skills/gitlab/SKILL.md
git commit -m "feat: add GitLab skill"
```

---

### Task 2: GitHub Skill

**Files:**
- Create: `skills/github/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: github
description: Use when working with GitHub — PRs, Actions, gh CLI, GitHub API, or any GitHub-related task
---

# GitHub

## Company Context

To get company-specific GitHub settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Find entries in `git.sources` where `provider: github` — use `org`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Pull Requests

```bash
gh pr list                                # list open PRs
gh pr create --title "title" --body "desc"  # create PR
gh pr view <number>                       # view PR details
gh pr diff <number>                       # view diff
gh pr checks <number>                     # CI status
gh pr merge <number> --squash             # merge with squash
gh pr review <number> --approve           # approve PR
```

### Actions / Workflows

```bash
gh run list                               # list workflow runs
gh run view <run-id>                      # run summary
gh run view <run-id> --log                # full logs
gh run rerun <run-id>                     # rerun failed
gh run watch <run-id>                     # live status
```

### Issues & Releases

```bash
gh issue list -l "bug"                    # list by label
gh issue create --title "title" --body "desc"
gh release list                           # list releases
gh release create <tag> --title "title" --notes "notes"
```

### API

```bash
gh api repos/<owner>/<repo>/pulls/<n>/comments   # PR comments
gh api repos/<owner>/<repo>/actions/runs          # workflow runs
```

## Runbooks

### Debug Failing Workflow

1. List recent runs: `gh run list`
2. View the failed run: `gh run view <run-id>`
3. Read full logs: `gh run view <run-id> --log`
4. Find the failed step and error message
5. If transient: `gh run rerun <run-id>`
6. If real failure: fix locally, push, monitor with `gh run watch`

### Review a Pull Request

1. View the PR: `gh pr view <number>`
2. Check CI: `gh pr checks <number>`
3. Review diff: `gh pr diff <number>`
4. Read comments: `gh api repos/<owner>/<repo>/pulls/<number>/comments`
5. Approve: `gh pr review <number> --approve`
6. Merge: `gh pr merge <number> --squash`

### Create a Release

1. Ensure all changes are merged to main
2. Tag: `git tag v<version>`
3. Push tag: `git push origin v<version>`
4. Create release: `gh release create v<version> --title "v<version>" --generate-notes`
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/github/SKILL.md
git add skills/github/SKILL.md
git commit -m "feat: add GitHub skill"
```

---

### Task 3: Favro Skill

**Files:**
- Create: `skills/favro/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: favro
description: Use when working with Favro — cards, boards, collections, task tracking, or any Favro-related task
---

# Favro

## Company Context

To get company-specific Favro settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `apps.favro` section — reads `organization_id`, `email`, `token_ref`

If no company is active, ask the user which company context to use.

Resolve the token: read `token_ref` from the config, then resolve via the appropriate secret backend (keychain or bitwarden).

## Commands

All Favro operations use the REST API. Set these variables from config:

```bash
FAVRO_ORG="<organization_id>"
FAVRO_EMAIL="<email>"
FAVRO_TOKEN="<resolved token>"
```

### List Collections

```bash
curl -s -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  "https://favro.com/api/v1/collections" | jq '.entities[].name'
```

### List Cards in Collection

```bash
curl -s -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  "https://favro.com/api/v1/cards?collectionId=<collection-id>" | jq '.entities[] | {name, columnId}'
```

### Move Card (Change Status)

```bash
curl -s -X PUT -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  -H "Content-Type: application/json" \
  -d '{"columnId":"<target-column-id>"}' \
  "https://favro.com/api/v1/cards/<card-id>"
```

### Add Comment to Card

```bash
curl -s -X POST -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  -H "Content-Type: application/json" \
  -d '{"comment":"<comment text>"}' \
  "https://favro.com/api/v1/cards/<card-id>/comments"
```

## Runbooks

### List Cards in a Collection

1. First list collections to find the collection ID
2. Then list cards in that collection
3. Parse the response to show card names and statuses

### Move Card to Done

1. List cards to find the card ID by name
2. List columns (via widget API) to find the "Done" column ID
3. PUT to update the card with the target `columnId`

### Add Work Summary Comment

1. Find the card ID by searching cards
2. Format a comment summarizing the work done
3. POST the comment to the card
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/favro/SKILL.md
git add skills/favro/SKILL.md
git commit -m "feat: add Favro skill"
```

---

### Task 4: Jira Skill

**Files:**
- Create: `skills/jira/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: jira
description: Use when working with Jira — issues, sprints, boards, jira CLI, or any Jira-related task
---

# Jira

## Company Context

To get company-specific Jira settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `apps.jira` section — reads `host`, `project`, `email`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Issues

```bash
jira issue list -q "project=<PROJECT> AND sprint in openSprints()"
jira issue view <KEY>-123
jira issue create -t Task -s "title" -b "description" -P <PROJECT>
jira issue move <KEY>-123 "In Progress"
jira issue comment add <KEY>-123 "comment text"
jira issue assign <KEY>-123 "username"
```

### Sprint

```bash
jira sprint list --board <board-id>
jira sprint list --board <board-id> --state active
```

### Search (JQL)

```bash
jira issue list -q "project=<PROJECT> AND assignee=currentUser() AND status != Done"
jira issue list -q "project=<PROJECT> AND type=Bug AND priority=High"
jira issue list -q "project=<PROJECT> AND updated >= -7d"
```

## Runbooks

### Create Task from Plan

1. Extract title and description from the plan
2. Create: `jira issue create -t Task -s "<title>" -b "<description>" -P <PROJECT>`
3. Move to In Progress: `jira issue move <KEY> "In Progress"`
4. Add implementation notes as comments

### Triage a Bug

1. Search for duplicates: `jira issue list -q "project=<PROJECT> AND type=Bug AND text ~ '<keywords>'"`
2. If duplicate exists, link to it and close as duplicate
3. If new: set priority, assign, add to current sprint
4. Add reproduction steps as a comment

### Close Sprint

1. List incomplete issues: `jira issue list -q "project=<PROJECT> AND sprint in openSprints() AND status != Done"`
2. For each incomplete issue: move to next sprint or backlog
3. Close the sprint via the web UI (no CLI support for sprint close)
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/jira/SKILL.md
git add skills/jira/SKILL.md
git commit -m "feat: add Jira skill"
```

---

### Task 5: Kubernetes Skill

**Files:**
- Create: `skills/kubernetes/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: kubernetes
description: Use when working with Kubernetes — pods, deployments, services, kubectl commands, cluster debugging, or any K8s-related task
---

# Kubernetes

## Company Context

To get company-specific Kubernetes settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.kubernetes` section — reads `kubeconfig`, `refresh.provider`, `refresh.cluster`

The `KUBECONFIG` env var should already be set by `ctx use`. If not, set it from the config.

## Commands

### Pods

```bash
kubectl get pods -n <ns>                              # list pods
kubectl get pods -n <ns> -o wide                      # with node info
kubectl describe pod <pod> -n <ns>                    # full details
kubectl logs -f <pod> -n <ns>                         # follow logs
kubectl logs -f <pod> -n <ns> -c <container>          # specific container
kubectl logs <pod> -n <ns> --previous                 # previous instance logs
kubectl logs -l app=<name> -n <ns> --prefix           # logs across pods by label
kubectl exec -it <pod> -n <ns> -- /bin/sh             # shell into pod
kubectl delete pod <pod> -n <ns>                      # delete pod (only when instructed)
```

### Deployments & Rollouts

```bash
kubectl get deployments -n <ns>
kubectl rollout status deployment/<name> -n <ns>      # watch rollout
kubectl rollout history deployment/<name> -n <ns>     # revision history
kubectl rollout undo deployment/<name> -n <ns>        # rollback (only when instructed)
kubectl scale deployment/<name> --replicas=<n> -n <ns>  # scale (only when instructed)
```

### Resources & Events

```bash
kubectl top pods -n <ns>                              # CPU/memory usage
kubectl top nodes                                     # node resource usage
kubectl get events -n <ns> --sort-by=.lastTimestamp   # recent events
kubectl get all -n <ns>                               # all resources
```

### Context

```bash
kubectl config get-contexts                           # list contexts
kubectl config current-context                        # current context
kubectl config use-context <name>                     # switch (only when instructed)
```

## Runbooks

### Debug CrashLoopBackOff

1. Describe the pod: `kubectl describe pod <pod> -n <ns>`
2. Check events at the bottom for error messages
3. Read previous instance logs: `kubectl logs <pod> -n <ns> --previous`
4. Check resource limits — OOM kills show as `OOMKilled` in `describe`
5. Check if readiness/liveness probes are misconfigured
6. If the container fails immediately, exec into a debug container or check the image

### Investigate OOM Kill

1. Confirm OOM: `kubectl describe pod <pod> -n <ns>` — look for `OOMKilled` in container status
2. Check current usage: `kubectl top pods -n <ns>`
3. Compare against limits in the deployment spec
4. If limits are too low: increase memory limits in the deployment
5. If there's a memory leak: check application logs, heap dumps

### Drain Node Safely

1. Cordon the node: `kubectl cordon <node>` (only when instructed)
2. Drain: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` (only when instructed)
3. Verify pods rescheduled: `kubectl get pods -o wide -A | grep <node>`
4. When maintenance is done: `kubectl uncordon <node>` (only when instructed)

### View Logs Across Pods

1. Find pods by label: `kubectl get pods -l app=<name> -n <ns>`
2. Stream all at once: `kubectl logs -l app=<name> -n <ns> --prefix -f`
3. For older logs or many pods, use `--since=1h` to limit scope
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/kubernetes/SKILL.md
git add skills/kubernetes/SKILL.md
git commit -m "feat: add Kubernetes skill"
```

---

### Task 6: Helm Skill

**Files:**
- Create: `skills/helm/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: helm
description: Use when working with Helm — charts, releases, values files, helm diff, or any Helm-related task
---

# Helm

## Company Context

To get company-specific Helm settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.kubernetes` section — Helm uses the same cluster context as kubectl

The `KUBECONFIG` env var should already be set by `ctx use`.

## Commands

### Releases

```bash
helm list -n <ns>                                     # list releases
helm status <release> -n <ns>                         # release status
helm history <release> -n <ns>                        # revision history
helm get values <release> -n <ns>                     # current values
helm get manifest <release> -n <ns>                   # rendered manifests
```

### Install & Upgrade

```bash
helm template <chart> . -f values.yaml               # render locally (safe)
helm diff upgrade <release> . -f values.yaml -n <ns>  # diff before apply (safe)
helm upgrade --install <release> . -f values.yaml -n <ns>  # apply (only when instructed)
helm upgrade --install <release> . -f values.yaml -n <ns> --dry-run  # dry run
```

### Rollback

```bash
helm rollback <release> <revision> -n <ns>            # rollback (only when instructed)
```

### Repos

```bash
helm repo list                                        # list repos
helm repo update                                      # update repo index
helm search repo <keyword>                            # search charts
```

## Runbooks

### Diff Before Upgrade

1. Always render locally first: `helm template <chart> . -f values.yaml`
2. Check the diff: `helm diff upgrade <release> . -f values.yaml -n <ns>`
3. Review every change carefully
4. Only apply when explicitly instructed: `helm upgrade --install <release> . -f values.yaml -n <ns>`

### Rollback Release

1. Check history: `helm history <release> -n <ns>`
2. Identify the last good revision number
3. Rollback (only when instructed): `helm rollback <release> <revision> -n <ns>`
4. Verify pods are healthy: `kubectl get pods -n <ns>`

### Template Locally

1. Render: `helm template <chart> . -f values.yaml`
2. Inspect the output for correctness
3. Check for common issues: missing values, wrong image tags, resource limits
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/helm/SKILL.md
git add skills/helm/SKILL.md
git commit -m "feat: add Helm skill"
```

---

### Task 7: Terraform Skill

**Files:**
- Create: `skills/terraform/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: terraform
description: Use when working with Terraform or OpenTofu — plan, apply, state, modules, terragrunt, or any IaC-related task
---

# Terraform / OpenTofu

## Company Context

To get company-specific Terraform settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.terraform` section — reads `vars` for `TF_VAR_*` env vars

`TF_VAR_*` env vars should already be set by `ctx use`.

## Commands

### Core Workflow

```bash
tofu init -backend=false                              # safe local init (no remote state)
tofu init                                             # full init with backend
tofu fmt                                              # format (required before commit)
tofu validate                                         # validate config
tflint                                                # lint
tofu plan -out=/tmp/plan.tfplan                       # plan to file
tofu apply /tmp/plan.tfplan                           # apply (only when instructed)
```

### State

```bash
tofu state list                                       # list resources
tofu state show <resource>                            # inspect resource
tofu state mv <old> <new>                             # rename (only when instructed)
tofu state rm <resource>                              # remove (only when instructed)
tofu import <resource> <id>                           # import (only when instructed)
```

### Terragrunt

```bash
terragrunt init
terragrunt plan
terragrunt apply                                      # only when instructed
terragrunt run-all plan                               # plan all modules
terragrunt run-all apply                              # only when instructed
terragrunt output
```

### Inspection

```bash
tofu output                                           # show outputs
tofu providers                                        # list providers
tofu graph | dot -Tpng > graph.png                    # dependency graph
```

## Runbooks

### Plan Safely

1. Format: `tofu fmt`
2. Validate: `tofu validate`
3. Lint: `tflint`
4. Plan to file: `tofu plan -out=/tmp/plan.tfplan`
5. Review the plan output carefully
6. Only apply when explicitly instructed

### Import Existing Resource

1. Add the resource block to your `.tf` files
2. Import: `tofu import <resource> <cloud-id>` (only when instructed)
3. Plan: `tofu plan` — should show no changes if import matches config
4. If there are diffs, adjust the config to match reality

### Fix State Drift

1. Plan: `tofu plan` to see what drifted
2. Decide: update config to match reality, or apply to make reality match config
3. If updating config: edit `.tf` files, plan again to verify no changes
4. If applying: `tofu apply` (only when instructed)

### Move State (Refactoring)

1. Plan the moves: identify old and new resource addresses
2. Move: `tofu state mv <old> <new>` (only when instructed)
3. Plan: verify no create/destroy, only in-place changes if any

**Safety:** Never run `tofu apply`, `tofu destroy`, `tofu state rm`, or `tofu import` without explicit user instruction.
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/terraform/SKILL.md
git add skills/terraform/SKILL.md
git commit -m "feat: add Terraform skill"
```

---

### Task 8: Ansible Skill

**Files:**
- Create: `skills/ansible/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: ansible
description: Use when working with Ansible — playbooks, inventory, ansible-vault, roles, or any Ansible-related task
---

# Ansible

## Company Context

To get company-specific Ansible settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `ssh` section — reads `keys` for SSH access to managed hosts

SSH keys should already be loaded by `ctx use`.

## Commands

### Playbooks

```bash
ansible-playbook -u <user> -i inventory/<file> <playbook>.yaml
ansible-playbook --vault-password-file .ansible_vault_pass <playbook>.yaml
ansible-playbook --check --diff <playbook>.yaml       # dry run (safe)
ansible-playbook -l <host-pattern> <playbook>.yaml     # limit to hosts
ansible-playbook -vvv <playbook>.yaml                  # verbose debug
```

### Vault

```bash
ansible-vault encrypt <file>                           # encrypt file
ansible-vault decrypt <file>                           # decrypt file
ansible-vault view <file>                              # view encrypted file
ansible-vault edit <file>                              # edit in-place
ansible-vault encrypt_string '<value>' --name '<var>'  # encrypt single value
```

### Linting

```bash
ansible-lint --profile min                             # lint playbooks
ansible-lint <playbook>.yaml                           # lint single file
```

### Ad-hoc

```bash
ansible <host-pattern> -i inventory/<file> -m ping     # test connectivity
ansible <host-pattern> -i inventory/<file> -m shell -a "uptime"  # run command
```

## Runbooks

### Run with Vault

1. Ensure vault password file exists: `.ansible_vault_pass` or prompted
2. Run: `ansible-playbook --vault-password-file .ansible_vault_pass -i inventory/<file> <playbook>.yaml`

### Limit to Specific Hosts

1. Check inventory: `ansible-inventory -i inventory/<file> --list`
2. Run with limit: `ansible-playbook -l <host-or-group> -i inventory/<file> <playbook>.yaml`

### Dry-Run (Check Mode)

1. Run: `ansible-playbook --check --diff -i inventory/<file> <playbook>.yaml`
2. Review the diff output — shows what WOULD change
3. Note: not all modules support check mode perfectly

### Debug Connection Issues

1. Test ping: `ansible <host> -i inventory/<file> -m ping`
2. If fails, add verbosity: `ansible <host> -i inventory/<file> -m ping -vvv`
3. Check SSH key, user, and host in inventory
4. Verify SSH agent has the right key: `ssh-add -l`
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/ansible/SKILL.md
git add skills/ansible/SKILL.md
git commit -m "feat: add Ansible skill"
```

---

### Task 9: Nomad Skill

**Files:**
- Create: `skills/nomad/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: nomad
description: Use when working with Nomad — jobs, allocations, deployments, nomad CLI, or any Nomad-related task
---

# Nomad

## Company Context

To get company-specific Nomad settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.nomad` section — reads `addr`, `token_ref`, `cacert`

`NOMAD_ADDR` and `NOMAD_TOKEN` should already be set by `ctx use`.

## Commands

### Jobs

```bash
nomad status                                          # list all jobs
nomad status <job>                                    # job detail
nomad job plan <job.nomad.hcl>                        # dry-run diff (safe)
nomad job run <job.nomad.hcl>                         # deploy (only when instructed)
nomad job stop <job>                                  # stop (only when instructed)
nomad job history <job>                               # deployment history
```

### Allocations

```bash
nomad alloc status <alloc-id>                         # allocation detail
nomad alloc logs <alloc-id>                           # stdout logs
nomad alloc logs -stderr <alloc-id>                   # stderr logs
nomad alloc logs -f -stderr <alloc-id>                # follow stderr
nomad alloc exec -task <task> <alloc-id> /bin/sh      # exec into alloc
```

### Nodes & Cluster

```bash
nomad node status                                     # list nodes
nomad node status <node-id>                           # node detail
nomad node drain -enable <node-id>                    # drain (only when instructed)
nomad operator raft list-peers                        # raft health
```

## Runbooks

### Debug Failed Allocation

1. Find the allocation: `nomad status <job>` — look at recent allocations
2. Check details: `nomad alloc status <alloc-id>`
3. Look at events for error messages (resource exhaustion, image pull failure, etc.)
4. Read logs: `nomad alloc logs <alloc-id>` and `nomad alloc logs -stderr <alloc-id>`
5. If resource exhaustion: check `nomad node status` for available resources

### Rolling Deploy

1. Plan first: `nomad job plan <job.nomad.hcl>` — review the diff
2. Deploy (only when instructed): `nomad job run <job.nomad.hcl>`
3. Monitor: `nomad status <job>` — watch deployment progress
4. If deployment fails: check allocation events and logs

### Drain Node

1. Drain (only when instructed): `nomad node drain -enable <node-id>`
2. Monitor: `nomad node status <node-id>` — watch allocations migrate
3. Verify all allocations rescheduled on other nodes
4. When done: `nomad node drain -disable <node-id>` (only when instructed)

### Read Allocation Logs

1. Find alloc ID: `nomad status <job>` — copy the allocation ID
2. Stdout: `nomad alloc logs <alloc-id>`
3. Stderr: `nomad alloc logs -stderr <alloc-id>`
4. Follow live: `nomad alloc logs -f -stderr <alloc-id>`

**Safety:** Never run `nomad job run`, `nomad job stop`, or `nomad system gc` without explicit instruction.
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/nomad/SKILL.md
git add skills/nomad/SKILL.md
git commit -m "feat: add Nomad skill"
```

---

### Task 10: Vault Skill

**Files:**
- Create: `skills/vault/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: vault
description: Use when working with HashiCorp Vault — secrets, auth, policies, vault CLI, or any Vault-related task
---

# HashiCorp Vault

## Company Context

To get company-specific Vault settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.vault` section — reads `addr`, `auth_method`, `token_ref`

`VAULT_ADDR` and `VAULT_TOKEN` should already be set by `ctx use`.

## Commands

### Status & Auth

```bash
vault status                                          # seal status, HA mode
vault token lookup                                    # current token info
vault login -method=token                             # login with token
vault login -method=ldap username=<user>              # login with LDAP
vault login -method=oidc                              # login with OIDC
```

### Secrets (KV v2)

```bash
vault secrets list                                    # mounted engines
vault kv list secret/<path>                           # list keys
vault kv get secret/<path>/<key>                      # read secret
vault kv get -format=json secret/<path>/<key>         # read as JSON
vault kv put secret/<path>/<key> foo=bar baz=qux      # write (only when instructed)
vault kv metadata get secret/<path>/<key>             # version history
vault kv rollback -version=<n> secret/<path>/<key>    # rollback (only when instructed)
```

### Policies

```bash
vault policy list                                     # list policies
vault policy read <policy>                            # read policy
vault policy write <policy> <file.hcl>                # write (only when instructed)
```

### Audit

```bash
vault audit list                                      # audit devices
```

## Runbooks

### Read Secrets Safely

1. List available paths: `vault kv list secret/<path>`
2. Read: `vault kv get -format=json secret/<path>/<key>`
3. Parse with jq if needed: `vault kv get -format=json secret/<path>/<key> | jq '.data.data'`

### Rotate Token

1. Check current token: `vault token lookup`
2. If TTL is low or expired: re-authenticate using the configured `auth_method`
3. For token auth: `vault login -method=token` (will prompt)
4. For LDAP: `vault login -method=ldap username=<user>`

### Check Seal Status

1. Run: `vault status`
2. Verify `Sealed: false`
3. Check HA mode and leader address
4. If sealed: this requires manual unsealing — escalate to the user

### Verify Audit Logging

1. List audit devices: `vault audit list`
2. Verify at least one audit device is enabled
3. If none: flag this as a security concern

**Safety:** Never write, delete, or modify secrets or policies without explicit instruction.
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/vault/SKILL.md
git add skills/vault/SKILL.md
git commit -m "feat: add Vault skill"
```

---

### Task 11: Consul Skill

**Files:**
- Create: `skills/consul/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: consul
description: Use when working with Consul — services, KV store, health checks, service mesh, or any Consul-related task
---

# Consul

## Company Context

To get company-specific Consul settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.consul` section — reads `addr`, `token_ref`

`CONSUL_HTTP_ADDR` and `CONSUL_HTTP_TOKEN` should already be set by `ctx use`.

## Commands

### Cluster

```bash
consul members                                        # cluster members
consul operator raft list-peers                       # raft health
consul monitor -log-level=debug                       # live log stream
```

### Services

```bash
consul catalog services                               # list all services
consul catalog nodes                                  # list all nodes
consul health checks <service>                        # health status
consul intention list                                 # service mesh intentions
```

### KV Store

```bash
consul kv get <key>                                   # read single key
consul kv get -recurse <prefix>/                      # list KV tree
consul kv put <key> <value>                           # write (only when instructed)
consul kv delete <key>                                # delete (only when instructed)
```

### DNS

```bash
dig @127.0.0.1 -p 8600 <service>.service.consul      # query Consul DNS
dig @127.0.0.1 -p 8600 <service>.service.consul SRV   # with port info
```

## Runbooks

### List Services and Health

1. List services: `consul catalog services`
2. For each service of interest: `consul health checks <service>`
3. Look for failing health checks — `Status: critical`

### Read KV Tree

1. Dump all keys under a prefix: `consul kv get -recurse <prefix>/`
2. Read a specific key: `consul kv get <key>`

### Check Cluster Health

1. List members: `consul members` — verify all nodes are `alive`
2. Check raft: `consul operator raft list-peers` — verify a leader exists
3. If no leader or members are `failed`: escalate immediately

### Debug Service DNS

1. Query Consul DNS: `dig @127.0.0.1 -p 8600 <service>.service.consul`
2. If no results: check if service is registered: `consul catalog services`
3. If registered but no DNS: check health — unhealthy services are excluded from DNS
4. Verify Consul DNS is configured as resolver for `.consul` domain

**Safety:** Never run `consul kv delete`, `consul leave`, or `consul force-leave` without explicit instruction.
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/consul/SKILL.md
git add skills/consul/SKILL.md
git commit -m "feat: add Consul skill"
```

---

### Task 12: Docker Skill

**Files:**
- Create: `skills/docker/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: docker
description: Use when working with Docker — containers, compose, building images, registries, or any Docker-related task
---

# Docker

## Company Context

To get company-specific Docker settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `docker.registries` section — reads `host`, `username_ref`, `password_ref`

Docker registry auth should already be configured by `ctx use`.

## Commands

### Containers

```bash
docker ps                                             # running containers
docker ps -a                                          # all containers
docker logs -f <container>                            # follow logs
docker logs --since 1h <container>                    # recent logs
docker exec -it <container> /bin/sh                   # shell into container
docker inspect <container>                            # full config
docker stats                                          # live resource usage
```

### Compose

```bash
docker compose up --build                             # build and start
docker compose up -d                                  # detached mode
docker compose logs -f <service>                      # follow service logs
docker compose down                                   # stop and remove
docker compose ps                                     # service status
docker compose exec <service> /bin/sh                 # shell into service
```

### Build & Push

```bash
docker build -t <tag> .                               # build image
docker build -t <tag> --no-cache .                    # build without cache
docker push <tag>                                     # push (only when instructed)
docker tag <source> <target>                          # retag image
```

### Registry

```bash
docker login <host> -u <user>                         # login
docker logout <host>                                  # logout
```

### Cleanup

```bash
docker system df                                      # disk usage
docker system prune                                   # remove unused (only when instructed)
docker system prune -a                                # remove all unused (only when instructed)
docker volume prune                                   # remove unused volumes (only when instructed)
```

## Runbooks

### Debug Container

1. Check if running: `docker ps | grep <name>`
2. Read logs: `docker logs --tail 100 <container>`
3. If running, exec in: `docker exec -it <container> /bin/sh`
4. Check config: `docker inspect <container>` — env vars, mounts, network
5. Check resource usage: `docker stats <container>`

### Rebuild from Scratch

1. Stop everything: `docker compose down`
2. Rebuild without cache: `docker compose build --no-cache`
3. Start: `docker compose up -d`
4. Verify: `docker compose ps` and `docker compose logs -f`

### Clean Up Disk Space

1. Check usage: `docker system df`
2. Remove stopped containers and dangling images: `docker system prune` (only when instructed)
3. For aggressive cleanup: `docker system prune -a` (only when instructed)
4. Clean volumes separately: `docker volume prune` (only when instructed)

### Registry Auth

1. Get credentials from ctx config (already done by `ctx use`)
2. Manual login if needed: `docker login <host> -u <user> --password-stdin`
```

- [ ] **Step 2: Verify and commit**

```bash
head -3 skills/docker/SKILL.md
git add skills/docker/SKILL.md
git commit -m "feat: add Docker skill"
```

---

### Task 13: `ctx skills deploy` Command

**Files:**
- Create: `src/ctx/skills.py`
- Modify: `src/ctx/cli.py`
- Create: `tests/test_skills.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
from unittest.mock import patch

from ctx.skills import deploy_skills, get_skills_source


def test_get_skills_source(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    # Write global config
    config_file = tmp_path / "config.yaml"
    config_file.write_text("skills_source: /path/to/skills\n")
    assert get_skills_source() == Path("/path/to/skills")


def test_get_skills_source_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    import pytest
    with pytest.raises(FileNotFoundError):
        get_skills_source()


def test_deploy_skills(tmp_path, monkeypatch):
    # Set up source skills
    source_dir = tmp_path / "source" / "skills"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")
    (source_dir / "github").mkdir(parents=True)
    (source_dir / "github" / "SKILL.md").write_text("---\nname: github\n---\n")

    target_dir = tmp_path / "projects"
    target_dir.mkdir()

    results = deploy_skills(source_dir, target_dir)

    # Check symlinks created
    assert (target_dir / ".claude" / "skills" / "gitlab").is_symlink()
    assert (target_dir / ".claude" / "skills" / "github").is_symlink()

    # Check CLAUDE.md created
    assert (target_dir / "CLAUDE.md").exists()
    assert "skills" in (target_dir / "CLAUDE.md").read_text().lower()

    assert len(results) == 2


def test_deploy_skills_updates_existing(tmp_path):
    source_dir = tmp_path / "source" / "skills"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")

    target_dir = tmp_path / "projects"
    target_dir.mkdir()

    # Deploy once
    deploy_skills(source_dir, target_dir)
    # Deploy again — should not fail
    results = deploy_skills(source_dir, target_dir)
    assert len(results) == 1
    assert (target_dir / ".claude" / "skills" / "gitlab").is_symlink()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skills.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ctx.skills'`

- [ ] **Step 3: Implement skills.py**

```python
from __future__ import annotations

from pathlib import Path

import yaml

from ctx.config import get_config_dir

PROJECTS_DIR = Path.home() / "projects"

CLAUDE_MD_CONTENT = """\
# Projects

Skills in `.claude/skills/` are available for all company work.
Active company config is at `~/.config/ctx/companies/<name>/config.yaml`.
"""


def get_skills_source() -> Path:
    config_file = get_config_dir() / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(
            f"Global config not found: {config_file}\n"
            f"Create it with:\n  skills_source: /path/to/your/skills"
        )
    with open(config_file) as f:
        config = yaml.safe_load(f)
    source = config.get("skills_source")
    if not source:
        raise FileNotFoundError("skills_source not set in global config")
    return Path(source)


def deploy_skills(
    source_dir: Path,
    target_dir: Path | None = None,
) -> list[str]:
    if target_dir is None:
        target_dir = PROJECTS_DIR

    skills_target = target_dir / ".claude" / "skills"
    skills_target.mkdir(parents=True, exist_ok=True)

    # Create CLAUDE.md if it doesn't exist
    claude_md = target_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(CLAUDE_MD_CONTENT)

    deployed = []
    for skill_dir in sorted(source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue

        link = skills_target / skill_dir.name
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            continue  # skip non-symlink existing dirs

        link.symlink_to(skill_dir)
        deployed.append(skill_dir.name)

    return deployed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_skills.py -v`
Expected: 4 passed

- [ ] **Step 5: Add CLI command to cli.py**

Add at the end of `src/ctx/cli.py`, before the last line:

```python
# --- Skills command ---

@main.group()
def skills():
    """Manage Claude Code skills."""


@skills.command("deploy")
def skills_deploy():
    """Deploy skills to ~/projects/.claude/skills/ as symlinks."""
    from ctx.skills import get_skills_source, deploy_skills
    source = get_skills_source()
    if not source.exists():
        click.echo(f"Skills source not found: {source}")
        return
    deployed = deploy_skills(source)
    if deployed:
        click.echo(f"Deployed {len(deployed)} skills: {', '.join(deployed)}")
    else:
        click.echo("All skills already deployed.")
```

- [ ] **Step 6: Test CLI command**

```python
# Add to tests/test_skills.py:

from click.testing import CliRunner
from ctx.cli import main


def test_skills_deploy_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))

    # Set up global config
    config_file = tmp_path / "config.yaml"
    source_dir = tmp_path / "skills_src"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")
    config_file.write_text(f"skills_source: {source_dir}\n")

    # Patch PROJECTS_DIR
    target = tmp_path / "projects"
    target.mkdir()
    monkeypatch.setattr("ctx.skills.PROJECTS_DIR", target)

    runner = CliRunner()
    result = runner.invoke(main, ["skills", "deploy"])
    assert result.exit_code == 0
    assert "Deployed 1 skills" in result.output
    assert (target / ".claude" / "skills" / "gitlab").is_symlink()
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add src/ctx/skills.py src/ctx/cli.py tests/test_skills.py
git commit -m "feat: ctx skills deploy command"
```

---

### Task 14: Projects CLAUDE.md Template

**Files:**
- Create: `templates/projects-claude.md`

This is the template that gets deployed to `~/projects/CLAUDE.md`.

- [ ] **Step 1: Create the template file**

```markdown
# Projects

Skills in `.claude/skills/` are available for all company work.
Active company config is at `~/.config/ctx/companies/<name>/config.yaml`.
```

- [ ] **Step 2: Commit**

```bash
git add templates/projects-claude.md
git commit -m "feat: add projects CLAUDE.md template"
```

---

### Task 15: Validate All Skills

**Files:**
- Create: `tests/test_skills_content.py`

A test that validates all skill files have correct structure.

- [ ] **Step 1: Write validation test**

```python
from pathlib import Path

import pytest
import yaml


SKILLS_DIR = Path(__file__).parent.parent / "skills"

EXPECTED_SKILLS = [
    "ansible",
    "consul",
    "docker",
    "favro",
    "github",
    "gitlab",
    "helm",
    "jira",
    "kubernetes",
    "nomad",
    "terraform",
    "vault",
]


def test_all_skills_exist():
    for name in EXPECTED_SKILLS:
        skill_file = SKILLS_DIR / name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {name}"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_valid_frontmatter(skill_name):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_file.read_text()

    # Must start with ---
    assert content.startswith("---"), f"{skill_name}: missing frontmatter"

    # Extract frontmatter
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{skill_name}: invalid frontmatter format"

    fm = yaml.safe_load(parts[1])
    assert "name" in fm, f"{skill_name}: missing 'name' in frontmatter"
    assert "description" in fm, f"{skill_name}: missing 'description' in frontmatter"
    assert fm["name"] == skill_name, f"{skill_name}: name mismatch"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_required_sections(skill_name):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_file.read_text()

    assert "## Company Context" in content, f"{skill_name}: missing Company Context section"
    assert "## Commands" in content, f"{skill_name}: missing Commands section"
    assert "## Runbooks" in content, f"{skill_name}: missing Runbooks section"
    assert "active_company" in content, f"{skill_name}: missing ctx config reading instructions"
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_skills_content.py -v`
Expected: All tests pass (1 + 12 + 12 = 25 tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_skills_content.py
git commit -m "feat: skill validation tests"
```
