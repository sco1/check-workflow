import os

# Set a dummy token so we don't hit the runtime error
# Token should not actually get used since we're mocking the API calls
os.environ["PUBLIC_PAT"] = "abc123"
