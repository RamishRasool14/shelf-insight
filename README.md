# Product Shelf Analysis Tool

A web-based application that uses Google's Gemini 2.5 Pro model to automatically detect and identify SKU items in retail product display images.

## 🚀 Features

- **Image Upload Interface**: Drag-and-drop upload for product display rack photos
- **SKU Configuration**: Customizable item detection lists with default retail items
- **AI-Powered Detection**: Google Gemini 2.5 Pro integration for automated product identification
- **JSON Export**: Download detection results in structured JSON format
- **Clean UI**: Google Material Design inspired interface with mobile responsiveness
- **Demo Mode**: Test the interface with sample detection results

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

3. **Configure SKU items**:
   - Use the default SKU list or create your custom list
   - Add items you want to detect in product shelf images

4. **Upload and analyze**:
   - Upload a product shelf image (PNG, JPG, JPEG, WebP)
   - Click "Analyze Product Shelf" to start detection
   - View results with item counts, locations, and confidence levels

5. **Export results**:
   - Download detection results as JSON file
   - Use data for inventory management or analytics

## 📁 Project Structure

```
mvp/
├── app.py                 # Main Streamlit application
├── gemini_client.py       # Google Gemini API integration
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