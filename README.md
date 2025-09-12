# OSA Image Analysis Tool

A web-based application that analyzes retail display images from OSA API and calculates accuracy metrics against ground truth data using Google's Gemini 2.5 Pro AI model.

## 🚀 Features

### Core Functionality
- **Date Selection**: Choose from last 10 days for historical analysis
- **Display ID Selection**: Select from configured display IDs (ACH187, ACH190, ACH186, ACH191, ACH192, ACH189, ACH188)
- **API Integration**: Direct integration with Tamimi OSA API for real-time image data
- **Filtered SKU Detection**: Uses only ground truth SKUs (OSA=1) for AI analysis
- **Display Image Viewing**: View original display images (AfterImagePath) with SKU details
- **SKU Image Access**: Click buttons to view individual SKU images when available

### Accuracy Metrics & Analysis
- **Ground Truth Extraction**: Automatically identifies SKUs with OSA=1 as ground truth
- **AI Prediction Comparison**: Compares Gemini AI predictions with ground truth data
- **Accuracy Calculation**: Calculates percentage of correctly detected SKUs
- **Detailed Breakdowns**: 
  - ✅ Correctly detected SKUs (True Positives)
  - ❌ Missed SKUs (False Negatives) 
  - ⚠️ False Positives (Predicted but not in ground truth)
- **Interactive Dropdowns**: View detailed lists of each category
- **Visual Indicators**: Color-coded predictions for easy comparison

### User Experience
- **Clean Layout**: Two-column design with images on left, predictions on right
- **Real-time Analysis**: Instant accuracy metrics after AI analysis
- **JSON Export**: Download detection results with accuracy data
- **Responsive Design**: Google Material Design inspired interface

### New: Analysis History (Supabase)
- **Automatic Persistence**: Each analysis run is saved to Supabase
- **History Viewer**: Load history per Date + Display ID
- **Previous/Next Navigation**: Browse historical runs (newest first)
- **Download Historical JSON**: Export raw detection from any run

## 🛠️ Technology Stack

- **Backend**: Python with Google Gen AI SDK (google-genai v1.22.0)
- **Frontend**: Streamlit for clean, interactive web interface
- **AI Model**: Google Gemini 2.5 Pro for image analysis
- **Image Processing**: PIL (Python Imaging Library)

## 📋 Prerequisites

- Python 3.8 or higher
- Google API key for Gemini API access
- Internet connection for API calls

## 🔧 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mvp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your Google API key
   GOOGLE_API_KEY=your_actual_api_key_here
   SUPABASE_URL=https://<your-project>.supabase.co
   SUPABASE_ANON_KEY=your_anon_key
   ```

4. **Get Google API Key**:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key for Gemini API
   - Copy the key to your `.env` file

## 🚀 Usage

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** and navigate to `http://localhost:8501`

3. **Select Analysis Parameters**:
   - Choose a date from the last 10 days using the dropdown
   - Select a Display ID from the available options (ACH187, ACH190, etc.)
   - Click "Fetch Images" to retrieve data from the OSA API

4. **Review Ground Truth Data**:
   - View original display images (AfterImagePath) on the left side
   - See SKU details for each display including Article numbers and UPC codes
   - Review Ground Truth SKUs (OSA=1) and All Available SKUs
   - Click "Show SKU Image" buttons to view individual product images

5. **Run AI Analysis**:
   - Click "Analyze Display Images" on the right panel
   - AI processes the display image using only ground truth SKUs (OSA=1)
   - View real-time accuracy metrics comparing predictions vs ground truth

6. **Analyze Results**:
   - **Accuracy Percentage**: Overall detection accuracy
   - **Correctly Detected SKUs**: ✅ Green indicators for true positives
   - **Missed SKUs**: ❌ Red indicators for false negatives
   - **False Positives**: ⚠️ Items predicted but not in ground truth
   - **Interactive Dropdowns**: Click to view detailed lists

7. **Export Data**:
   - Download detection results with accuracy metrics as JSON
   - Use data for model performance analysis and improvement

8. **History**:
   - After running an analysis, scroll to "Analysis History"
   - Click "Load History" to fetch past runs by selected Date + Display ID
   - Use "Previous"/"Next" to navigate between runs (newest first)
   - Download the raw detection JSON of any historical run

## 📁 Project Structure

```
mvp/
├── app.py                 # Main Streamlit application
├── gemini_client.py       # Google Gemini API integration
├── supabase_client.py     # Supabase helpers for saving/fetching runs
├── config.py             # Configuration settings and constants
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
└── README.md            # Project documentation
```

## 🎨 Design Features

- **Color Scheme**: Google Material Design colors
  - Primary: #4285F4 (Google Blue)
  - Secondary: #34A853 (Google Green)
  - Background: #F8F9FA (Light Grey)
  - Success: #137333 (Dark Green)

- **Responsive Layout**: Works on desktop and mobile devices
- **Card-based Design**: Clean, organized information display
- **Intuitive Navigation**: Clear visual hierarchy and user flow

## 🔧 Configuration Options

### Default SKU Items
The application includes common retail items:
- Coca-Cola bottles
- Pepsi bottles
- Water bottles
- Energy drinks
- Juice boxes
- Snack bars
- Chips/Crisps
- Candy/Sweets
- Bread loaves
- Milk cartons

### File Upload Limits
- Maximum file size: 10MB
- Supported formats: PNG, JPG, JPEG, WebP

### Detection Settings
- Model: Google Gemini 2.5 Pro
- Confidence levels: High, Medium, Low
- Location detection: Shelf position identification

## 📊 Output Format

Detection results are provided in JSON format:

```json
{
  "detected_items": [
    {
      "item_name": "Coca-Cola bottles",
      "quantity": 12,
      "location": "Top shelf, left section",
      "confidence": "high",
      "notes": "Classic red Coca-Cola bottles, clearly visible"
    }
  ],
  "total_items_detected": 1,
  "analysis_timestamp": "2024-01-15T10:30:00"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Error**:
   - Verify your Google API key is correct
   - Ensure Gemini API is enabled for your project
   - Check API quota and billing settings

2. **File Upload Issues**:
   - Check file size (max 10MB)
   - Verify file format is supported
   - Ensure stable internet connection

3. **Detection Problems**:
   - Use high-quality, well-lit images
   - Ensure products are clearly visible
   - Adjust SKU list to match actual products

### Demo Mode
Use demo mode to test the interface without API calls:
- Enable "Demo Mode" in the sidebar
- Upload any image to see sample detection results
- Perfect for development and testing

## 🔐 Security

- API keys are stored in environment variables
- File uploads are validated for type and size
- No persistent storage of uploaded images
- Secure API communication with Google services
- Supabase anon key is used client-side; restrict RLS policies appropriately

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Google Gemini API documentation
3. Open an issue in the repository
4. Contact the development team

## 🔮 Future Enhancements

- Batch image processing
- Advanced analytics dashboard
- Integration with inventory management systems
- Custom model training options
- Real-time detection via camera feed
- Multi-language support

## 📚 Supabase Setup

Create a table `osa_analysis_runs` with the following schema (Postgres):

```sql
create table public.osa_analysis_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  date text not null,
  display_id text not null,
  ground_truth_skus jsonb not null,
  predicted_skus jsonb not null,
  accuracy numeric,
  metrics jsonb not null,
  raw_detection jsonb not null,
  image_url text
);

-- Helpful index for lookups by date+display
create index on public.osa_analysis_runs (date, display_id, created_at desc);

-- Basic RLS (adjust to your needs)
alter table public.osa_analysis_runs enable row level security;
create policy "read all" on public.osa_analysis_runs for select using (true);
create policy "insert all" on public.osa_analysis_runs for insert with check (true);
```

Environment variables required:

```bash
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

The app uses these helpers in `supabase_client.py`:
- `save_osa_run(...)` to insert a new run
- `fetch_runs(date_str=..., display_id=..., limit=50)` to load history