FROM rasa/rasa-sdk:3.6.0

USER root

RUN apt-get update && apt-get install -y curl iputils-ping && rm -rf /var/lib/apt/lists/*
RUN pip install requests

USER 1001

CMD ["start", "--actions", "actions.actions", "--port", "5055"]
