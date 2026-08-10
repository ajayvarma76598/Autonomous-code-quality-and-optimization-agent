from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Autonomous Code Quality & Optimization System",
    description="API for managing code quality and optimization tasks",
    version="0.1.0",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Autonomous Code Quality & Optimization System API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":

    main()
