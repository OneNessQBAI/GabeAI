import streamlit as st
import subprocess
import plotly.graph_objects as go
from datetime import datetime
import json
import os
from bs4 import BeautifulSoup
import sys
import io
from contextlib import redirect_stdout
from openai import OpenAI
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with DeepSeek configuration
client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com/v1"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

def chat_with_deepseek(messages):
    try:
        response = client.chat.completions.create(
            model="deepseek-coder",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error communicating with DeepSeek API: {str(e)}")
        return None

def clear_chat():
    st.session_state.messages = []

def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return str(e)

def execute_python_script(script):
    try:
        output = io.StringIO()
        with redirect_stdout(output):
            exec(script)
        return output.getvalue()
    except Exception as e:
        return str(e)

def search_duckduckgo(query):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for result in soup.find_all('div', class_='result'):
            title = result.find('a', class_='result__a')
            snippet = result.find('a', class_='result__snippet')
            if title and snippet:
                results.append({
                    'title': title.text.strip(),
                    'snippet': snippet.text.strip(),
                    'url': title['href']
                })
        return results[:5]  # Return top 5 results
    except Exception as e:
        return [{"error": str(e)}]

def create_visualization(data):
    try:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                pass
        
        if isinstance(data, dict):
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(data.keys()),
                          fill_color='paleturquoise',
                          align='left'),
                cells=dict(values=list(data.values()),
                          fill_color='lavender',
                          align='left'))
            ])
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            headers = list(data[0].keys())
            values = [[d[k] for d in data] for k in headers]
            fig = go.Figure(data=[go.Table(
                header=dict(values=headers,
                          fill_color='paleturquoise',
                          align='left'),
                cells=dict(values=values,
                          fill_color='lavender',
                          align='left'))
            ])
        elif isinstance(data, str):
            fig = go.Figure()
            fig.add_annotation(
                text=data,
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
        else:
            return None
            
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        return fig
    except:
        return None

st.title("DeepSeek v3 Hackaton Gabe's AI ")

# Add clear chat button in sidebar
with st.sidebar:
    if st.button("Clear Chat History"):
        clear_chat()

# System prompt to format responses
SYSTEM_PROMPT = """⚠️you are a Hackaton AI be interactive with the user but when coding  COPY AND PASTE THESE EXACT FORMATS - DO NOT MODIFY THEM!

❌ THESE WILL BE REJECTED:
- Raw text outside code blocks
- Scripts without try/except blocks
- Mixed code block types
- Incorrect block names
- Empty code blocks

✅ COPY THESE FORMATS EXACTLY:

1️⃣ FOR SCRIPTS - USE BOTH BLOCKS:
First block MUST be:
```response
Here's a script that checks system information including CPU, memory, and disk usage
```

Second block MUST be:
```script
try:
    # Your code here
    import psutil
    print(psutil.cpu_percent())
except Exception as e:
    print(f"Error: {e}")
```

2️⃣ FOR COMMANDS - USE BOTH BLOCKS:
First block MUST be:
```response
This command will show all active network connections and listening ports
```

Second block MUST be:
```command
netstat -an
```

3️⃣ FOR SEARCHES - ONE BLOCK ONLY:
```search
latest cybersecurity tools 2024
```

4️⃣ FOR VISUALIZATIONS - USE BOTH BLOCKS:
First block MUST be:
```response
This visualization shows real-time system performance metrics
```

Second block MUST be:
```visualization
{
    "metric": "value",
    "data": [1, 2, 3]
}
```

⚠️ CRITICAL RULES:
1. COPY these formats EXACTLY
2. DO NOT modify the block types
3. Scripts MUST have try/except
4. NO text outside blocks
5. NO mixing block types
6. Commands/scripts need response block first
7. Search/visualization use exact format shown

✅ VALID BLOCK TYPES:
- ```response``` - For explanations
- ```script``` - For Python code (with try/except)
- ```command``` - For system commands
- ```search``` - For web searches
- ```visualization``` - For data visualization

⚠️ REMEMBER:
- COPY the formats above EXACTLY
- DO NOT modify or improvise
- ALWAYS use try/except in scripts
- NO raw text allowed
"""

# Chat input
user_input = st.chat_input("Enter your message...")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        # Prepare messages for API call
        api_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        # Get AI response
        content = chat_with_deepseek(api_messages)
        
        if content:
            # Strict response validation and formatting
            def format_response(content):
                # Split into code blocks
                parts = content.split('```')
                if len(parts) < 3:  # Must have at least one code block
                    return ["```response\nPlease provide a properly formatted response.\n```"]
                
                formatted_parts = []
                current_type = None
                
                for i in range(1, len(parts), 2):
                    block = parts[i].strip()
                    if not block:
                        continue
                    
                    # Extract block type and content
                    lines = block.split('\n', 1)
                    if len(lines) < 2:
                        continue
                    
                    block_type = lines[0].strip()
                    block_content = lines[1].strip()
                    
                    # Validate block type
                    valid_types = ['script', 'command', 'search', 'visualization', 'response']
                    if block_type not in valid_types:
                        block_type = 'response'
                        block_content = block
                    
                    # Enforce response block first for script/command
                    if current_type is None and block_type in ['script', 'command'] and not any('```response' in p for p in parts[:i]):
                        formatted_parts.append(f"```response\nHere's the {block_type} to execute:\n```")
                    
                    # Format block
                    if block_type == 'script' and ('try:' not in block_content or 'except' not in block_content):
                        block_content = f"try:\n{block_content}\nexcept Exception as e:\n    print(f'Error: {{e}}')"
                    
                    formatted_parts.append(f"```{block_type}\n{block_content}\n```")
                    current_type = block_type
                
                return formatted_parts if formatted_parts else ["```response\nPlease provide a properly formatted response.\n```"]
            
            # Format and add responses
            formatted_parts = format_response(content)
            for part in formatted_parts:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": part
                })
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        
        # Handle command blocks
        if "```command" in content:
            command = content.split("```command")[1].split("```")[0].strip()
            st.code(command, language="bash")
            button_key = f"cmd_{len(st.session_state.messages)}_{abs(hash(command))}"
            if st.button(f"Execute Command", key=button_key):
                result = execute_command(command)
                st.code(result, language="bash")
        
        # Handle script blocks
        elif "```script" in content:
            script = content.split("```script")[1].split("```")[0].strip()
            st.code(script, language="python")
            button_key = f"script_{len(st.session_state.messages)}_{abs(hash(script))}"
            if st.button(f"Run Script", key=button_key):
                result = execute_python_script(script)
                st.code(result, language="python")
        
        # Handle search blocks
        elif "```search" in content:
            query = content.split("```search")[1].split("```")[0].strip()
            st.code(f"Searching for: {query}", language="bash")
            results = search_duckduckgo(query)
            fig = create_visualization(results)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Handle visualization blocks
        elif "```visualization" in content:
            viz_data = content.split("```visualization")[1].split("```")[0].strip()
            fig = create_visualization(viz_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Display regular response
        else:
            st.markdown(content)

st.sidebar.markdown("""
### Features
- Execute Python scripts
- Run system commands
- Web search via DuckDuckGo
- Data visualization
- Powered by DeepSeek AI

### Response Formats
1. Scripts: ```script```
2. Commands: ```command```
3. Search: ```search```
4. Visualization: ```visualization```
5. Text: ```response```

### Tips
- Scripts and commands are executed safely
- Web search provides up-to-date information
- Visualizations are created automatically
""")
