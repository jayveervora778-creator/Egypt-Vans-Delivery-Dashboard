module.exports = {
  apps: [{
    name: 'streamlit_dashboard',
    script: 'python',
    args: '-m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true',
    cwd: '/home/user/webapp_fresh',
    env: {
      'PYTHONPATH': '/home/user/webapp_fresh',
      'STREAMLIT_DASH_PASSWORD': 'vans2025', // Dashboard password
      'STREAMLIT_DISABLE_DATAFRAME_ARROW_CONVERSION': '1'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    interpreter: 'none' // Don't use PM2's built-in interpreter detection
  }]
};