
import logging
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectClassifier:
    def __init__(self):
        # Initialize the vectorizer with specific settings for code patterns
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            token_pattern=r'[A-Za-z0-9\-]+',  # Pattern to match code subject format
            lowercase=True
        )

        # Extended training data for departments based on codeSujet patterns
        self.train_data = {
            'Informatique': ['MI', 'ISI', 'SI2', 'INFO'],
            'Electronique': ['ENG', 'ELEC'],
            'Mechanique': ['PROD', 'MEC'],
            'Genie Civil': ['BAT', 'GC'],
            'Mathematiques': ['MA'],
            'Process Control': ['P&C', 'CPI'],
            'Industrial Design': ['DI']
        }

        # Extract department code from codeSujet
        def extract_dept_code(code):
            if not isinstance(code, str):
                return str(code)
            # Remove any whitespace and convert to uppercase
            code = code.strip().upper()
            
            # Try to find matching department code
            for dept, patterns in self.train_data.items():
                if any(pattern.upper() in code for pattern in patterns):
                    return dept
            
            # Handle different code formats
            parts = code.split('-')
            if len(parts) >= 2:
                # Extract department code from format L-DEPTXX-XXX
                dept_code = parts[1][:2] if parts[1].startswith('MA') else parts[1][:3]
                dept_code = ''.join(filter(str.isalpha, dept_code))  # Remove numbers
                
                for dept, patterns in self.train_data.items():
                    if any(pattern.upper() == dept_code.upper() for pattern in patterns):
                        return dept
            
            # Try finding any pattern in the full code
            for dept, patterns in self.train_data.items():
                if any(pattern.upper() in code.upper() for pattern in patterns):
                    return dept
            
            return "Other"  # Default category if no match found

        self.extract_dept_code = extract_dept_code

        # Prepare training data
        X_train = []
        y_train = []
        for dept, codes in self.train_data.items():
            for code in codes:
                X_train.append(code)
                y_train.append(dept)

        # Fit vectorizer and train classifier
        X_train_vec = self.vectorizer.fit_transform(X_train)
        self.classifier = MultinomialNB()
        self.classifier.fit(X_train_vec, y_train)

    def classify_project(self, subject):
        """
        Classify a project subject into a department
        Returns department name
        """
        try:
            if not isinstance(subject, str):
                subject = str(subject)
            
            # Direct pattern matching first
            department = self.extract_dept_code(subject)
            if department != "Other":
                logger.info(f"Classified '{subject}' as '{department}' using pattern matching")
                return department
                
            # Fallback to ML classification
            subject_vec = self.vectorizer.transform([subject])
            department = self.classifier.predict(subject_vec)[0]
            
            logger.info(f"Classified '{subject}' as '{department}' using ML")
            return department

        except Exception as e:
            logger.error(f"Error classifying project: {str(e)}")
            return "Unclassified"

# Initialize classifier
classifier = ProjectClassifier()

def read_training_data(file_path):
    """Read and process Excel file for training data"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                break
            except Exception as e:
                continue
                
        if df is not None and 'codeSujet' in df.columns:
            codes = df['codeSujet'].dropna().unique()
            return list(codes)
        return []
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return []

if __name__ == "__main__":
    # Try to read from Excel file
    training_data = read_training_data("attached_assets/liste-SFE-22_23.xlsx")
    
    if training_data:
        print("\nProcessing data from Excel file:")
        for subject in training_data[:5]:  # Show first 5 examples
            dept = classifier.classify_project(subject)
            print(f"\nSubject: {subject}")
            print(f"Classified as: {dept}")
    else:
        # Fallback to test examples
        test_subjects = [
            "L-MI23-001",
            "L-ENG23-027",
            "L-BAT23-014",
            "L-MA23-014"
        ]
        
        for subject in test_subjects:
            dept = classifier.classify_project(subject)
            print(f"\nSubject: {subject}")
            print(f"Classified as: {dept}")
