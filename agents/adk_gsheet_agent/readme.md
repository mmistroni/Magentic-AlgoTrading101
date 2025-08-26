### Pre Steps 
# you need to activate .bashrc

. ~/.bashrc

gcloud auth application-default login

python -m venv myenv && source myenv/bin/activate

gcloud auth application-default login

adk web

https://github.com/bhancockio/


deploy to cloud
https://github.com/google/adk-samples/blob/main/python/agents/academic-research/README.md


###
This directory contains an agent that handle a holiday budget stored in a google spreadsheet
The Agent basic operations are
- get current budget
- insert an expense

