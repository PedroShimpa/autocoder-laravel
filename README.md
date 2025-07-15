# Auto Programming with Ollama Based on Test Results

## Initial Objective

This tool automates code creation and correction by analyzing test results. For example:

- You write a test that validates if a route `/users` returns a list of website users.
- The auto-coder will then:
  - Create the route, controller, and view.
  - Inspect migrations and models to determine if a database table already exists or needs to be created.
 
With this, you only need code the tests and the autocoder make all the other things for you.

## To the future

 - The autocoder learn all your existent project and improve this, make corrections, add features and make commits, only with your prompt! 

This approach enables incremental, test-driven automatic programming with Laravel.

---

## How to Run

1. **Create an Ollama model**  
   Build your custom Ollama model using your `Modelfile`:

   ```bash
   ollama create meu-modelo -f Modelfile

2. **Run the auto-coding script**
```bash
python ollama_cmd.py --user "Corrija o erro no arquivo X.php conforme os testes falharam."
Notes

The script runs php artisan test repeatedly, sending test results to the Ollama model.

Ollama returns code edits or new file creations that the script applies automatically.

The process repeats until tests pass or a maximum number of attempts is reached.
