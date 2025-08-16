module.exports = {
  apps: [{
    name: 'vans-dashboard',
    script: 'streamlit',
    args: 'run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true',
    cwd: '/home/user/webapp_fresh',
    env: {
      'PYTHONPATH': '/home/user/webapp_fresh',
      'STREAMLIT_DASH_PASSWORD': '' // Set password here if needed
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
};