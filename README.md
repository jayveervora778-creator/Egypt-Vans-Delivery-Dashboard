# 🚐 Vans Data Interactive Dashboard

A professional, interactive dashboard for analyzing delivery operations data built with Streamlit.

## ✨ Features

- 🔐 **Optional Password Protection** - Secure your dashboard with environment variables
- 📊 **Interactive Data Analysis** - Custom pivot tables and aggregations
- 📈 **Rich Visualizations** - Multiple chart types with Plotly
- 🔍 **Advanced Filtering** - Filter by company, employment status, age, and more
- 📋 **KPI Dashboard** - Key performance indicators at a glance
- 📥 **Data Export** - Download filtered data as CSV
- 🎨 **Professional UI** - Clean, modern interface with custom styling

## 🚀 Quick Start

### Deploy to Streamlit Cloud (Recommended)

1. **Fork this repository** to your GitHub account
2. **Go to [share.streamlit.io](https://share.streamlit.io)**
3. **Click "New app"**
4. **Select your forked repository**
5. **Set Main file path:** `app.py`
6. **Deploy!**

Your dashboard will be live in minutes at: `https://your-app-name.streamlit.app`

### Run Locally

```bash
# Clone the repository
git clone https://github.com/your-username/vans-dashboard.git
cd vans-dashboard

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run app.py
```

## 🔒 Security (Optional)

To enable password protection, set an environment variable:

**Streamlit Cloud:**
- Go to app settings
- Add secret: `STREAMLIT_DASH_PASSWORD = "your-password"`

**Local:**
```bash
export STREAMLIT_DASH_PASSWORD="your-password"
streamlit run app.py
```

## 📊 Data Format

The dashboard works with Excel (.xlsx) or CSV files containing delivery/operations data. 

**Expected columns include:**
- Company
- Employment Status
- Age (Years)
- Deliveries per day
- Medical Insurance
- Net Income (Gross - All Expenses) (EGP)
- Areas Covered
- Fuel Expenses (EGP)
- Maintenance Costs (EGP)

## 🛠️ Customization

### Adding New Charts
Edit `app.py` and add new visualizations in the "Visualizations" section.

### Custom Styling
Modify the CSS in the `st.markdown()` section at the top of `app.py`.

### New KPIs
Add metrics in the "Key Performance Indicators" section.

## 📱 Mobile Friendly

The dashboard is responsive and works well on mobile devices.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use and modify as needed.

---

**Built with ❤️ using Streamlit**