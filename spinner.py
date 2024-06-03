import streamlit as st
import time

# Create a progress bar with initial progress of 0%
progress_bar = st.progress(0)

# Simulate a long-running task
for i in range(100):
    # Update the progress bar
    progress_bar.progress(i + 1)
    # Simulate some work
    time.sleep(0.1)

# Display a success message after completion
st.success("Done!")
