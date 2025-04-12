import os
import requests
import subprocess
import shutil
from tqdm import tqdm

def check_sudo():
    if os.geteuid() != 0:
        print("Este script requer privilégios de superusuário. Solicitando sudo...")
        subprocess.run(["sudo", "python3"] + os.sys.argv)
        exit(1)

def get_latest_stable_kernel():
    url = "https://kernel.org/releases.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            stable_release = next((r for r in data["releases"] if r["moniker"] == "stable"), None)
            if stable_release:
                return stable_release["version"], stable_release["source"], stable_release["pgp"]
        print("Erro ao acessar ou processar as releases do kernel.org")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Erro ao acessar kernel.org: {e}")

    return None, None, None

def download_file(url, output_path, max_retry = 3):
    for attempt in range(max_retry):
        if not os.path.exists(output_path):
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                total_size = int(response.headers.get("content-length", 0))
                with open(output_path, "wb") as file, tqdm(
                    desc=os.path.basename(output_path),
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            bar.update(len(chunk))
                return True
            else:
                print(f"Erro ao baixar {url}")
        else:
            print (f"Arquivo {output_path} já existe, pulando o download")
            return True
    return False

def verify_pgp(signature, source):
    result = subprocess.run(f"xz -cd {source} | gpg --verify {signature} -", shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("Assinatura PGP verificada com sucesso!")
        return True
    else:
        print("Falha na verificação da assinatura PGP:")
        print(result.stderr)
        return False


def compile_kernel(version, config_file=".config"):
    project_dir = f"linux-{version}"
    if not os.path.exists(project_dir):
        os.mkdir(project_dir)
    subprocess.run(["tar", "-xf", f"linux-{version}.tar.xz", "-C", project_dir, "--strip-components=1"], check=True)
    subprocess.run(["cp", config_file, f"{project_dir}/.config"], check=True)
    subprocess.run(["cp", "-r", "certs/*", f"{project_dir}/certs"], check=True)
    os.chdir(project_dir)

    steps = [
        "make olddefconfig",
        "make -j$(nproc)",
        "make modules_install",
        "make install"
    ]

    for step in tqdm(steps, desc="Compilando o kernel"):
        subprocess.run(step, shell=True, check=True)

    print("Kernel compilado e instalado com sucesso")

def check_dependencies():
    dependencies = ["xz", "gpg", "make", "tar"]
    for dep in dependencies:
        if not shutil.which(dep):
            print(f"Erro: '{dep}' não encontrado. Instale antes de continuar.")
            exit(1)


def main():
    check_sudo()
    check_dependencies()

    version, source_url, pgp_url = get_latest_stable_kernel()
    if version and source_url and pgp_url:
        print(f"Última versão estável do kernel: {version}")
        source_file = f"linux-{version}.tar.xz"
        sig_file = f"linux-{version}.tar.sign"

        if not download_file(source_url, source_file):
            exit(1)
        if not download_file(pgp_url, sig_file):
            exit(1)

        if verify_pgp(sig_file, source_file):
            compile_kernel(version)
            subprocess.run("rm", f"linux-{version}.tar.*", shell=True, check=True)
        else:
            print("Falha na verificação PGP. Abortando.")
    else:
        print("Não foi possível determinar a última versão estável do kernel.")

if __name__ == "__main__":
    main()

