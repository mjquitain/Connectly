# Connectly

A Django REST Framework-based social media platform that enables users to create posts, interact through comments and likes, and authenticate via traditional credentials or Google OAuth.

## 🎯 Features

- **User Management**
  - User registration and authentication
  - Token-based authentication
  - Google OAuth 2.0 integration
  
- **Posts System**
  - Multiple post types (text, image, video)
  - Post metadata support (file size, duration, etc.)
  - Post pagination for efficient data loading
  
- **Social Interactions**
  - Comment on posts
  - Like posts (with unique user-post constraint)
  - Personalized news feed
  
- **Security**
  - Permission-based access control
  - Author-only edit/delete permissions
  - Admin-only protected routes

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)
- SQLite (default database)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone [<repository-url>](https://github.com/mjquitain/Connectly.git)
   cd Connectly
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv env
   
   # Windows
   .\env\Scripts\activate
   
   # Linux/Mac
   source env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install django djangorestframework djangorestframework-simplejwt django-cors-headers django-extensions
   ```

4. **Apply database migrations**
   ```bash
   cd connectly_project
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## 📁 Project Structure

```
Connectly/
├── connectly_project/          # Main Django project
│   ├── connectly_project/      # Project settings
│   │   ├── settings.py         # Django configuration
│   │   ├── urls.py             # Main URL routing
│   │   └── wsgi.py             # WSGI configuration
│   ├── posts/                  # Core application
│   │   ├── models.py           # Database models
│   │   ├── views.py            # API views
│   │   ├── serializers.py      # REST serializers
│   │   ├── permissions.py      # Custom permissions
│   │   ├── urls.py             # App URL routing
│   │   └── google_auth.py      # Google OAuth handler
│   ├── factories/              # Design pattern implementations
│   │   └── post_factory.py     # Factory for creating posts
│   ├── singletons/             # Singleton pattern implementations
│   │   ├── config_manager.py   # Configuration management
│   │   └── logger_singleton.py # Logging system
│   ├── manage.py               # Django management script
│   └── db.sqlite3              # SQLite database
└── env/                        # Virtual environment
```

## 🗃️ Database Models

### ConnectlyUser
Custom user model for the platform
- `username`: Unique username
- `email`: Unique email address
- `created_at`: Account creation timestamp

### Post
User-generated content with type classification
- `title`: Post title
- `post_type`: Type (text/image/video)
- `content`: Post content
- `metadata`: JSON field for type-specific data
- `author`: Foreign key to ConnectlyUser
- `created_at`: Post creation timestamp

### Comment
User comments on posts
- `text`: Comment content
- `author`: Foreign key to ConnectlyUser
- `post`: Foreign key to Post
- `created_at`: Comment creation timestamp

### Like
User likes on posts (unique per user-post pair)
- `user`: Foreign key to ConnectlyUser
- `post`: Foreign key to Post
- `created_at`: Like timestamp

### GoogleSocialAccount
Links ConnectlyUser to Google OAuth accounts
- `user`: One-to-one with ConnectlyUser
- `google_id`: Unique Google user ID
- `email`: Google account email
- `name`: User's name from Google
- `picture_url`: Profile picture URL
- `last_login`: Last authentication timestamp

## 🔐 Authentication

Connectly supports two authentication methods:

### 1. Token Authentication
Traditional username/password with token-based sessions

**Register**: `POST /register/`
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "password_confirm": "securepassword"
}
```

**Login**: `POST /login/`
```json
{
  "username": "johndoe",
  "password": "securepassword"
}
```

**Response includes token**:
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": { ... }
}
```

### 2. Google OAuth
Authenticate using Google accounts

**Endpoint**: `POST /auth/google/login/`
```json
{
  "id_token": "<google-id-token>"
}
```

## 🔑 Using Authentication Tokens

Include the token in the Authorization header for protected endpoints:

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

## 🏗️ Design Patterns

### Factory Pattern
**PostFactory** (`factories/post_factory.py`)
- Encapsulates post creation logic
- Validates post type and required metadata
- Ensures consistent post creation

```python
PostFactory.create_post(
    post_type='image',
    title='My Photo',
    author=user,
    content='Beautiful sunset',
    metadata={'file_size': 1024000}
)
```

### Singleton Pattern
**LoggerSingleton** (`singletons/logger_singleton.py`)
- Provides a single logger instance throughout the application
- Ensures consistent logging configuration

**ConfigManager** (`singletons/config_manager.py`)
- Centralized configuration management
- Single source of truth for application settings

## 🛡️ Custom Permissions

- **IsPostAuthor**: Only post authors can edit/delete their posts
- **IsCommentAuthor**: Only comment authors can edit/delete their comments
- **IsAdminOrReadOnly**: Read access for all, write access for admins only

**Built with Django REST Framework** 🚀
