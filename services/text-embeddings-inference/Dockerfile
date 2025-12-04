# Custom TEI image with pre-downloaded nomic-embed-text-v1.5 model
# Based on official TEI CPU image
FROM ghcr.io/huggingface/text-embeddings-inference:cpu-1.8

# Install Python and huggingface_hub to download model
USER root
RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir --break-system-packages huggingface_hub && \
    rm -rf /var/lib/apt/lists/*

# Set HuggingFace cache directory (TEI uses this)
ENV HF_HOME=/data

# Pre-download the model during build
# This downloads to /data which is where TEI will look for it
RUN python3 -c "from huggingface_hub import snapshot_download; \
    snapshot_download('nomic-ai/nomic-embed-text-v1.5', \
                      cache_dir='/data')"

# Clean up Python (optional - reduces image size)
RUN apt-get remove -y python3 python3-pip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Switch back to non-root user (TEI runs as UID 1000)
USER 1000

# TEI will automatically find the model in /data when MODEL_ID is set

