# This folder contains agents written using AWS Bedrock
Youtube:  https://www.youtube.com/live/wzIQDPFQx30?si=j41vdyDQqQrGncsk

https://github.com/awslabs/amazon-bedrock-agentcore-samples


# You need to initialize environment using the requirements in aws directory

pip install --force-reinstall -U -r requirements.txt --quiet

https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent/01-strands-with-bedrock-model/runtime_with_strands_and_bedrock_models.ipynb


# To Run strand agent
python ./strands_claude.py   '{"prompt": "What is 2 + 2 and what is the weather?"}'