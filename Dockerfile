FROM python:3.11-slim

RUN useradd -m -u 1000 user

USER user
ENV HOME=/home/user
ENV PATH=$HOME/.local/bin:$PATH
WORKDIR $HOME/app

COPY --chown=user requirements.txt $HOME/app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=user . $HOME/app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
