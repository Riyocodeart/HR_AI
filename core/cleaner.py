class DataCleaner:
    
    PENALTIES = {
    "missing_name": 20,
    "missing_role": 15,
    "missing_location": 5,
    "missing_skills": 25,
    "missing_company": 5,
    "missing_education": 10,
    "invalid_email": 10,
    "invalid_experience": 20,
    }
    ACCEPTED_SCORE = 80
    REVIEW_SCORE = 50

    def clean(self, df):
        df["quality_score"] = 100
        df["warnings"] = ""
        
        df = self.standardize_names(df)
        df = self.standardize_roles(df)
        df = self.standardize_locations(df)
        df = self.standardize_skills(df)
        df = self.standardize_companies(df)
        df = self.standardize_education(df)
        df = self.standardize_emails(df)
        df = self.standardize_experience(df)

        df = self.validate_names(df)
        df = self.validate_roles(df)
        df = self.validate_locations(df)
        df = self.validate_skills(df)
        df = self.validate_companies(df)
        df = self.validate_education(df)
        df = self.validate_emails(df)
        df = self.validate_experience(df)

        df=self.classify_candidates(df)

        
    
        return df
        
    def standardize_names(self, df):

        df["name"] = (
            df["name"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
        )

        return df

    def standardize_roles(self, df):

        df["role"] = (
            df["role"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
        )

        return df

    def standardize_locations(self, df):

        location_map = {
            "Bombay": "Mumbai",
            "Mumbai, India": "Mumbai",
            "Bangalore": "Bengaluru"
        }

        df["location"] = (
            df["location"]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace(location_map)
        )

        return df

    def standardize_skills(self, df):

        df["skills"] = (
            df["skills"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        return df

    def standardize_companies(self, df):

        df["company"] = (
            df["company"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
        )

        return df

    def standardize_education(self, df):

        df["education"] = (
            df["education"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
        )

        return df

    def standardize_emails(self, df):

        df["email"] = (
            df["email"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        return df

    def standardize_experience(self, df):

        df["experience"] = (
            df["experience"]
            .fillna(0)
            .astype(float)
        )

        return df

    def validate_names(self, df):

        mask = df["name"].isna() | (df["name"].str.strip() == "")
    
        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_name"]

        df.loc[mask, "warnings"] += "Missing Name; "

        return df

    def validate_roles(self, df):

        mask = df["role"].isna() | (df["role"].str.strip() == "")

        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_role"]

        df.loc[mask, "warnings"] += "Missing Role; "

        return df

    def validate_locations(self, df):

        mask = df["location"].isna() | (df["location"].str.strip() == "")

        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_location"]

        df.loc[mask, "warnings"] += "Missing Location; "

        return df

    def validate_skills(self, df):

        mask = df["skills"].isna() | (df["skills"].str.strip() == "")

        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_skills"]

        df.loc[mask, "warnings"] += "Missing Skills; "

        return df

    def validate_companies(self, df):

        mask = df["company"].isna() | (df["company"].str.strip() == "")

        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_company"]

        df.loc[mask, "warnings"] += "Missing Company; "

        return df

    def validate_education(self, df):

        mask = df["education"].isna() | (df["education"].str.strip() == "")

        df.loc[mask, "quality_score"] -= self.PENALTIES["missing_education"]

        df.loc[mask, "warnings"] += "Missing Education; "

        return df

    def validate_emails(self, df):

        mask = (
            df["email"].isna()
        |   (df["email"].str.strip() == "")
        |   (~df["email"].str.contains("@", na=False))
        )   

        df.loc[mask, "quality_score"] -= self.PENALTIES["invalid_email"]

        df.loc[mask, "warnings"] += "Invalid Email; "

        return df

    def validate_experience(self, df):

        mask = (df["experience"] < 0) | (df["experience"] > 50)

        df.loc[mask, "quality_score"] -= self.PENALTIES["invalid_experience"]

        df.loc[mask, "warnings"] += "Invalid Experience; "

        return df

    def classify_candidates(self, df):

        df["status"] = "Accepted"

        df.loc[df["quality_score"] < self.ACCEPTED_SCORE, "status"] = "Needs Review"
        
        df.loc[df["quality_score"] < self.REVIEW_SCORE, "status"] = "Rejected"

        return df