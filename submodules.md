start:
git switch llm_traces_bottleneck 
git pull --recurse-submodules 
git submodule update --init --recursive 
git submodule foreach --recursive 'git switch llm_traces_bottleneck || true'

end:
git status
git submodule foreach --recursive 'echo "===== $path ====="; git status -sb'