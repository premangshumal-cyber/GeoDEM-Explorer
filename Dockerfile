FROM mambaorg/micromamba:2.3.2
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba create -y -f /tmp/environment.yml && micromamba clean --all --yes
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app
ENV PATH=/opt/conda/envs/geodem-explorer/bin:$PATH
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["bash", "-lc", "exec uvicorn app.main:app --host 0.0.0.0 --port \${PORT:-8000}"]
