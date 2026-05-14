from src.ipl_analysis import run_analysis


if __name__ == "__main__":
    artifacts = run_analysis()
    print(artifacts.summary_markdown)
