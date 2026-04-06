from __future__ import annotations


def generate_shell_init(shell: str) -> str:
    if shell != "zsh":
        raise ValueError(f"Unsupported shell: {shell}")

    return """\
# hat shell integration

# Common aliases and completions
[[ -f ~/projects/common/aliases.sh ]] && source ~/projects/common/aliases.sh
[[ -f ~/projects/common/completions.sh ]] && source ~/projects/common/completions.sh

# hat env and prompt
_hat_precmd() {
  local env_file="${HAT_CONFIG_DIR:-$HOME/Library/hat}/state.env"
  if [[ -f "$env_file" ]]; then
    source "$env_file"
  fi
  local state_file="${HAT_CONFIG_DIR:-$HOME/Library/hat}/state.json"
  if [[ -f "$state_file" ]]; then
    export HAT_ACTIVE=$(python3 -c "import json,sys;d=json.load(open('$state_file'));print(d.get('active_company',''))" 2>/dev/null)
  else
    unset HAT_ACTIVE
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd _hat_precmd

# Prompt indicator
if [[ -n "$HAT_ACTIVE" ]]; then
  RPROMPT="[${HAT_ACTIVE}] ${RPROMPT}"
fi
"""
