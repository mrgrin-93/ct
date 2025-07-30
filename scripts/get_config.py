from getpass import getuser
from nornir import InitNornir
from nornir_scrapli.tasks import cfg_get_config, get_prompt
from nornir.core.task import Task, Result
from nornir.core.exceptions import NornirSubTaskError
from scrapli.exceptions import ScrapliAuthenticationFailed
from git import Repo
from datetime import datetime
import  argparse
import pexpect

def get_host_conf(task: Task):
    try:
        result = task.run(task=cfg_get_config)
        hn = task.run(task=get_prompt)
        with open(f'/usr/local/Cisco/confs/{hn.result.strip("#")}', "w") as file:
           file.write(result.scrapli_response.result) 
    except NornirSubTaskError:
        pass
    except ScrapliAuthenticationFailed as e:
        pass
    except AttributeError as e:
        pass

parser = argparse.ArgumentParser()
parser.add_argument("-H", dest="host", default=None, help='hostname')
args = parser.parse_args()

nr = InitNornir(config_file="/opt/ct/config.yaml",
                logging={"enabled": False, "log_file": "/opt/ct/nornir.log"})

if args.host:
    host_name = args.host
    hosts = nr.filter(name=host_name.lower())
    try:
        hosts.run(task=get_host_conf)
    except NornirSubTaskError:
        pass
    except ScrapliAuthenticationFailed:
        pass
    except AttributeError as e:
        pass
#    except:
#        pass

    PATH_OF_GIT_REPO = '/usr/local/Cisco/confs/.git'
    user = getuser()
    date = datetime.now()
    repo = Repo(PATH_OF_GIT_REPO)
    repo.git.add(all=True)
    repo.index.commit(f'{date} {user}')

else:
    nr.run(task=get_host_conf)

    PATH_OF_GIT_REPO = '/usr/local/Cisco/confs/.git'
    repo = Repo(PATH_OF_GIT_REPO)
    repo.git.add(all=True)
    date = datetime.now()
    repo.index.commit(f'Dayly commit {date}')
    child = pexpect.spawn('git push')
    child.expect(pexpect.EOF)
    child.close()
