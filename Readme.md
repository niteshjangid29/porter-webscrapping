<h1 align="center">porter-api-unofficial</h1>
<p align="center"><em>🚛 Because manually checking Porter quotes is so 2023</em></p>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/niteshjangid29/porter-api-unofficial?style=flat&logo=git&color=blue" />
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg?style=flat&logo=python" />
  <img src="https://img.shields.io/badge/Selenium-Automation-green.svg?style=flat&logo=selenium" />
</p>

---

## 🎭 About This Project

An **unofficial Python package** that automates delivery quote retrieval from **[Porter.in](https://porter.in/)** using **Selenium**.  
It can be used both as a **library** and a **standalone script**, supports **multiple cities & service types**, and integrates with **AWS SQS** for async workflows.

⚠️ **Disclaimer**
- 🚫 Not affiliated with, endorsed by, or connected to Porter.in  
- 🎓 For educational & research purposes only  
- 🙏 Respect Porter's Terms of Service  

---

## ✨ Features

- 🔎 **Automated Quote Retrieval** – Fetch delivery quotes programmatically
- 🏙️ **City & Service Type Support** – Two wheelers, trucks, packers & movers  
- ⚡ **Selenium Automation** – Mimics user actions in Chrome to bypass manual work  
- 🛠️ **Error Handling** – Custom exceptions (`exceptions.py`) for robustness  
- 📦 **AWS SQS Consumer** – Async message processing via `sqs_consumer.py`  
- ⚙️ **Config Management** – Centralized settings in `config.py`  
- 🧑‍💻 **Modular Codebase** – Clean separation:  
  - `app.py` → High-level API  
  - `core.py` → Low-level scraping logic  
  - `exceptions.py` → Error classes  
  - `sqs_consumer.py` → Queue worker  
  - `main.py` → CLI entrypoint  

---

## 🚀 Installation

```sh
# Clone repository
git clone https://github.com/niteshjangid29/porter-api-unofficial.git
cd porter-api-unofficial

# Install dependencies
pip install -r requirements.txt
```


## 🎮 Quick Start
### Method 1 – Library Usage

```
from porter_api.app import PorterAPI

porter = PorterAPI(name="John Doe", phone="9876543210")
quote = porter.get_quote(
    pickup_address="Koramangala, Bangalore",
    drop_address="Electronic City, Bangalore",
    city="Bangalore",
    service_type="trucks"
)

print("Got quotes:", quote)
```

### Method 2 – Direct Function

```sh
from porter_api.core import get_porter_quote

quote = get_porter_quote(
    name="Jane Smith",
    phone="9876543210",
    pickup_address="Bandra, Mumbai",
    drop_address="Andheri, Mumbai",
    city="Mumbai",
    service_type="two_wheelers"
)

print("Zoom zoom! 🏍️", quote)
```

### Method 3 – CLI
```sh
python main.py --name "Ravi" --phone "9876543210" \
  --pickup "HSR Layout, Bangalore" --drop "BTM Layout, Bangalore" \
  --city "Bangalore" --service trucks
```

## 📋 API Reference

### PorterAPI Class
```sh
class PorterAPI:
    def __init__(self, name: str, phone: str, headless: bool = True)
    def get_quote(
        self,
        pickup_address: str,
        drop_address: str,
        city: str,
        service_type: str = "trucks"
    ) -> Dict
```

### Helper Functions
```sh
get_porter_quote(name, phone, pickup_address, drop_address, city, service_type)
get_supported_cities() -> List[str]
get_supported_service_types() -> List[str]
```

## 📊 Response Format

### ✅ Success
```sh
{
  "success": true,
  "pickup_address": "Koramangala, Bangalore",
  "drop_address": "Electronic City, Bangalore",
  "city": "Bangalore",
  "service_type": "trucks",
  "user_name": "Arjun Rampal",
  "user_phone": "9876546843",
  "quotes": [
    {
      "vehicle_name": "3 Wheeler",
      "price_range": "₹585 - ₹615",
      "min_price": 585,
      "max_price": 615,
      "capacity": "500 kg",
      "capacity_kg": 500
    }
  ],
  "timestamp": "2025-09-13 15:30:00"
}
```

### ❌ Error
```sh
{
  "success": false,
  "error": "Invalid phone number",
  "details": "Phone must be 10 digits",
  "suggestion": "Remove country code and try again"
}
```

## 🌍 Supported Cities

- Bangalore
- Mumbai
- Delhi
- Chennai
- Hyderabad
- Pune


## 🚛 Service Types

- "two_wheelers" 🏍️

- "trucks" 🚚

- "packers_and_movers" 📦

## 🐛 Error Handling

Custom exceptions are defined in `exceptions.py`:

- `InvalidPhoneNumberError`

- `UnsupportedCityError`

- `UnsupportedServiceTypeError`

- `ScrapingError`

## 📡 Advanced: AWS SQS Consumer

This project also comes with `sqs_consumer.py` which consumes messages from an AWS SQS queue and triggers quote scraping automatically.

### Example message body:
```sh
{
  "name": "Amit",
  "phone": "9876543210",
  "pickup": "Kalyan Nagar, Bangalore",
  "drop": "Indiranagar, Bangalore",
  "city": "Bangalore",
  "service": "trucks"
}
```

## consumer:
```sh
python sqs_consumer.py
```

## 🛠️ Roadmap
- Docker support for easy deployment
- Async scraping with Playwright
- CI/CD integration