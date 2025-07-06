from setuptools import setup, find_packages

setup(
    name="llm_bridge",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'fastapi>=0.68.0',
        'uvicorn>=0.15.0',
        'python-jose[cryptography]>=3.3.0',
        'passlib[bcrypt]>=1.7.4',
        'python-multipart>=0.0.5',
        'pymongo>=3.12.0',
        'python-dotenv>=0.19.0',
        'sentence-transformers>=2.2.0',
        'numpy>=1.21.0',
        'pydantic>=1.8.0',
        'requests>=2.26.0',
        'streamlit>=1.10.0',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    package_data={
        '': ['*.json', '*.pkl', '*.bin'],
    },
    entry_points={
        'console_scripts': [
            'bridge=api.main:main',
        ],
    },
)