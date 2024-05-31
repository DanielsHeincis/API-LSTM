import os
import re
import subprocess
import shutil
import sys
import argparse

def check_program_installed(program):
    """Check if a program is installed."""
    try:
        subprocess.run([program, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print(f"{program} is installed.")
    except subprocess.CalledProcessError:
        print(f"Error: {program} is not installed.")
        return False
    except FileNotFoundError:
        print(f"Error: {program} is not installed.")
        return False
    return True

def check_python_package_installed(package):
    """Check if a Python package is installed."""
    try:
        __import__(package)
        print(f"{package} is installed.")
    except ImportError:
        print(f"Error: {package} is not installed.")
        return False
    return True

def check_requirements():
    """Check if all required programs and packages are installed."""
    required_programs = ['git']
    required_packages = ['re', 'os', 'subprocess', 'shutil', 'sys', 'argparse']

    all_installed = True

    for program in required_programs:
        if not check_program_installed(program):
            all_installed = False

    for package in required_packages:
        if not check_python_package_installed(package):
            all_installed = False

    return all_installed

def extract_urls(text, repo, file_path):
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    partial_url_pattern = re.compile(
    r'(?:^|\s|["\'])(?!.*//)(?!.*\*{2})(?!.*\/\*[-=])(\./[\w./]*|\.\./[\w./]*|/[\w./]*)(?=\s|$|["\'])(?!.*,)'
    )

    forward_slash_pattern = re.compile(
    r'(?:^|\s|["\'])(?!.*//)(?!.*\*{2})(?!.*\/\*[-=])(/[^\s"\'<>]*)?(?=\s|$|["\'])(?!.*,)'
    )
    
    full_urls = [(url.rstrip(','), 'FULL_URL', repo, file_path, i+1) for i, url in enumerate(url_pattern.findall(text))]
    partial_urls = [(url.rstrip(','), 'PARTIAL_URL', repo, file_path, i+1) for i, url in enumerate(partial_url_pattern.findall(text))]
    forward_slash_strings = [(url.rstrip(','), 'FORWARD_SLASH', repo, file_path, i+1) for i, url in enumerate(forward_slash_pattern.findall(text))]

    return full_urls + clean_urls(partial_urls) + clean_urls(forward_slash_strings)

def clean_urls(urls_to_clean):
    cleaned_tuples = []
    for url_to_clean_tulpe in urls_to_clean:
        url_to_clean = url_to_clean_tulpe[0]
        # Remove "./" and "../" from the beginning of the path
        while url_to_clean.startswith("./") or url_to_clean.startswith("../"):
            url_to_clean = url_to_clean.lstrip("./")
            url_to_clean = url_to_clean.lstrip("../")
        
        # Ensure each line starts with "/"
        if not url_to_clean.startswith("/"):
            url_to_clean = "/" + url_to_clean
            
        modified_tuple = (url_to_clean,) + url_to_clean_tulpe[1:]
        cleaned_tuples.append(modified_tuple)
    
    return cleaned_tuples


def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except UnicodeDecodeError:
        print(f"Cannot read file (binary or unknown encoding): {file_path}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def search_directory_for_urls(directory, forbidden_characters):
    all_urls = {
        'FULL_URL': set(),
        'PARTIAL_URL': set(),
        'FORWARD_SLASH': set()
    }
    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if not is_text_file(file_path):
                continue
            content = read_file(file_path)
            if content is not None:
                repo = os.path.basename(os.path.dirname(file_path))
                urls = extract_urls(content, repo, file_path)
                for url, flag, _, _, _ in urls:
                    if any(char in url for char in forbidden_characters):
                        continue
                    all_urls[flag].add(url)
    return all_urls

def is_text_file(file_path):
    """Check if a file is a text file by reading a portion of its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.read(1024)
        return True
    except:
        return False

def clone_github_repo(repo_url, clone_dir):
    try:
        subprocess.run(['git', 'clone', repo_url, clone_dir], check=True)
        print(f"Successfully cloned {repo_url}")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")

def cleanup_directory(directory):
    try:
        shutil.rmtree(directory)
        print(f"Cleaned up directory: {directory}")
    except Exception as e:
        print(f"Error cleaning up directory {directory}: {e}")

def process_repo(repo_url, output_file, append):
    clone_dir = 'cloned_repo'
    clone_github_repo(repo_url, clone_dir)
    forbidden_characters = [
    ' ', '"', '<', '>', '\\', '^', '`', '{', '}', '[', ']', '|', '\x7F', ')', '(', '@'
    ]
    urls = search_directory_for_urls(clone_dir, forbidden_characters)
    mode = 'a' if append else 'w'
    with open(output_file, mode, encoding='utf-8') as f:
        for flag, url_set in urls.items():
            if flag == 'FULL_URL':
                f.write("FULL_URLS:\n")
            elif flag == 'PARTIAL_URL':
                f.write("\nPARTIAL_URLS:\n")
            elif flag == 'FORWARD_SLASH':
                f.write("\nFORWARD_SLASHES:\n")
            for url in url_set:
                f.write(f"{flag}: {url}\n")
    cleanup_directory(clone_dir)
    
    
def process_dir(dir_path, output_file, append):
    forbidden_characters = [
    ' ', '"', '<', '>', '\\', '^', '`', '{', '}', '[', ']', '|', '\x7F', ')', '('
    ]
    urls = search_directory_for_urls(dir_path, forbidden_characters)
    mode = 'a' if append else 'w'
    with open(output_file, mode, encoding='utf-8') as f:
        for flag, url_set in urls.items():
            for url in url_set:
                f.write(f"{flag}: {url}\n")
 

def main():
    if not check_requirements():
        print("Please install the missing programs or packages and try again.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Extract URLs from files or a GitHub repository.')
    parser.add_argument('--dir', type=str, help='Local directory to search for files')
    parser.add_argument('--repo', type=str, help='GitHub repository URL')
    parser.add_argument('--file', type=str, help='File containing GitHub repository URLs (one per line)')
    parser.add_argument('--output', type=str, required=True, help='Output file to save extracted URLs')
    parser.add_argument('--append', action='store_true', help='Append to existing output file (default is overwrite)')
    args = parser.parse_args()

    if args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: Directory {args.dir} does not exist.")
            sys.exit(1)
        process_dir(args.dir, args.output, args.append)
    elif args.repo:
        process_repo(args.repo, args.output, args.append)
    elif args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File {args.file} does not exist.")
            sys.exit(1)
        with open(args.file, 'r', encoding='utf-8') as f:
            repo_urls = f.readlines()
        for repo_url in repo_urls:
            process_repo(repo_url.strip(), args.output, args.append)
    else:
        print("Error: You must specify either --dir, --repo, or --file.")
        parser.print_help()
        sys.exit(1)
        
if __name__ == '__main__':
    main()