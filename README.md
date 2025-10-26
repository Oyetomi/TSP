# Tennis Set Prediction System

## 79% Prediction Accuracy

A statistical tennis prediction system specializing in +1.5 set betting markets. Built on advanced statistical analysis, multi-year performance data, and comprehensive risk management.

![Tennis Prediction Dashboard](assets/prediction-dashboard.png)
*Interactive prediction dashboard with real-time analysis and filtering*

---

## Overview

A data-driven tennis prediction system that analyzes player performance across multiple dimensions to predict match outcomes with 79% accuracy. The system focuses on +1.5 set predictions, identifying matches where the favored player is likely to win at least one set.

### Key Metrics

- **Prediction Accuracy**: ~79%
- **Analysis Depth**: Multi-year statistical modeling
- **Data Sources**: SofaScore match data, UTR ratings, ATP/WTA rankings
- **Prediction Focus**: +1.5 set markets (player wins ≥1 set)

---

## Core Features

### Statistical Analysis
- **Multi-year performance blending** - Weighted analysis across 2-3 years of data
- **Surface-specific modeling** - Separate analysis for Hard, Clay, and Grass courts
- **Opponent quality adjustment** - Performance normalized against opponent strength
- **Recent form emphasis** - Current performance weighted more heavily
- **UTR integration** - Universal Tennis Rating for true skill assessment

### Risk Management
- **Data quality gates** - Automatic skip for insufficient data samples
- **Sample size thresholds** - Minimum match/set requirements enforced
- **Ranking gap penalties** - Hot streak detection prevents false signals
- **Bagel risk indicators** - High-risk match identification
- **Confidence scoring** - Match-by-match reliability assessment

### Advanced Features
- **Mental toughness metrics** - Clutch performance and competitive resilience
- **Return of serve analysis** - Hannah Fry principle implementation
- **Momentum tracking** - Recent match trends and streaks
- **Tournament classification** - Grand Slam vs regular tournament adjustments
- **Injury filtering** - Automatic exclusion of recently injured players

---

## Technical Architecture

### Backend
- **Language**: Python 3.9
- **API Framework**: FastAPI
- **Data Processing**: Pandas, NumPy
- **HTTP Client**: curl-cffi (bypasses rate limiting)
- **Prediction Model**: Statistical weighted analysis (not ML)

### Frontend
- **Framework**: Next.js 14 with TypeScript
- **UI Library**: shadcn/ui components
- **Styling**: Tailwind CSS
- **State Management**: SWR for data fetching
- **Features**: Real-time filtering, match selection, odds integration

### Data Sources
- **Match Data**: SofaScore API
- **Odds**: SportyBet integration
- **Player Ratings**: UTR (Universal Tennis Rating)
- **Rankings**: ATP/WTA official rankings

---

## Installation

### Prerequisites
```bash
Python 3.9+
Node.js 18+ (for frontend)
```

### Backend Setup
```bash
# Clone repository
git clone https://github.com/yourusername/tennis-set-prediction.git
cd tennis-set-prediction

# Install Python dependencies
pip install -r requirements.txt

# Configure API credentials
cp api_secrets.example.py api_secrets.py
# Edit api_secrets.py with your API keys
```

### Frontend Setup
```bash
cd frontend
pnpm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with API endpoints

# Run development server
pnpm dev
```

---

## Usage

### Running Predictions
```bash
# Generate predictions for today's matches
python3.9 main.py

# Run with specific date
python3.9 main.py --date 2025-10-26

# Run backend server
python3.9 run_server.py
```

### Accessing the Dashboard
```bash
cd frontend
pnpm dev
# Navigate to http://localhost:3000
```

---

## Prediction Model

### Weight Configuration (FORM_OPTIMIZED_OCT2025)

| Factor | Weight | Description |
|--------|--------|-------------|
| Set Performance | 30% | Historical set win rate against quality opponents |
| Recent Form | 23% | Current performance and momentum |
| UTR Rating | 10% | Universal skill assessment |
| Ranking Advantage | 8% | ATP/WTA ranking differential |
| Return of Serve | 8% | Return game effectiveness |
| Surface Performance | 8% | Court-specific win rates |
| Momentum | 5% | Recent match trends |
| Serve Dominance | 3% | Ace rate and first serve percentage |
| Pressure Performance | 3% | Break point conversion |
| Tiebreak Performance | 2% | Clutch performance in tiebreaks |

### Skip Logic

Matches are automatically excluded when:
- Either player has < 5 sets of data (insufficient sample)
- Either player has 0 current-year matches on surface (pure extrapolation)
- Either player has < 30% win rate with ≥4 matches (extreme poor form indicator)
- Network data quality issues detected

---

## Performance History

| Version | Accuracy | Key Improvement |
|---------|----------|----------------|
| v1.0 | 45% | Initial ATP ranking-based model |
| v2.0 | 55% | Added UTR ratings |
| v3.0 | 62% | Surface-specific analysis |
| v4.0 | 68% | Multi-year data blending |
| v5.0 | 73% | Enhanced form weighting |
| v6.0 | 74% | Loss analysis and opponent quality |
| **v7.0** | **79%** | Hot streak detection and data quality gates |

---

## Dashboard Features

### Match Filtering
- Surface type (Hard, Clay, Grass)
- Gender (Men's, Women's)
- Confidence level (Low, Medium, High)
- Edge percentage thresholds
- Odds ranges
- Risk levels

### Selection Tools
- Bulk match selection
- Player-specific betting (dual mode)
- Random selection for testing
- Same-country exclusion
- Ranking-based filters

### Risk Indicators
- Bagel risk warnings (0-6 set potential)
- Data quality assessments
- Sample size indicators
- Ranking gap alerts

---

## API Integration

### Odds Provider
Integrates with SportyBet API for:
- Real-time odds fetching
- +1.5 and +2.5 set markets
- Automated bet slip generation
- Share code creation

### Match Data Provider
SofaScore integration provides:
- Comprehensive match history
- Player statistics
- Head-to-head records
- Tournament information

---

## Configuration Management

### Weight Profiles
Multiple pre-configured weight profiles available:
- `FORM_OPTIMIZED_OCT2025` - Current active (79% accuracy)
- `HOT_STREAK_74PCT` - Original baseline
- `CLUTCH_V2_20251026` - Class over form emphasis

### Multi-Year Modes
- 2-year mode: 70% current, 30% previous year
- 3-year mode: Blended weighted analysis

---

## Project Structure

```
tennis-set-prediction/
├── app/                    # FastAPI application
│   ├── core/              # Configuration
│   ├── models/            # Data models
│   ├── routers/           # API endpoints
│   └── services/          # Business logic
├── frontend/              # Next.js dashboard
│   ├── src/
│   │   ├── app/          # Pages and API routes
│   │   └── components/   # React components
├── scripts/               # Analysis scripts
├── tests/                 # Test suites
└── utils/                 # Utility functions
```

---

## Development

### Adding New Weight Configurations
```python
from weight_config_manager import config_manager

config_manager.add_config(
    code_name="MY_CONFIG",
    name="My Configuration",
    description="Description here",
    weights={...},
    features={...}
)
```

### Running Tests
```bash
pytest tests/
```

---

## Disclaimer

This system is designed for research and educational purposes. Users should:
- Understand betting involves financial risk
- Implement proper bankroll management
- Verify predictions independently
- Comply with local gambling regulations
- Use predictions as one input in decision-making

Past performance does not guarantee future results.

---

## License

MIT License - See LICENSE file for details

---

## Contact & Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact: [your-email]

---

*Last Updated: October 2025*
*Current Version: 7.0*
*Status: Production*
