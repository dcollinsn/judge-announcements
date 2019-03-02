# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # Install vb-guest to manage Guest Additions
  # Install disksize to enable config.disksize option (which may not be necessary)
  required_plugins = %w( vagrant-vbguest vagrant-disksize )
  _retry = false
  required_plugins.each do |plugin|
    unless Vagrant.has_plugin? plugin
      system "vagrant plugin install #{plugin}"
        _retry=true
      end
  end

  if (_retry)
    exec "vagrant " + ARGV.join(' ')
  end

  config.vm.box = "ubuntu/bionic64"
  config.disksize.size = "10GB"
  config.vm.network "forwarded_port", guest: 8080, host: 8087
  config.vm.synced_folder ".", "/announcements"
  config.vm.provider "virtualbox" do |vb|
      vb.customize ["modifyvm", :id, "--memory", "2048"]
  end

  config.vm.provision "shell", inline: <<SCRIPT

# Expand partition (no argument expands it to its maximum size)
sudo resize2fs /dev/sda1

# Configure and install OS packages
sudo apt-get update

apt-get install -y python3.7 python3-pip \
    git mercurial python3.7-dev build-essential \
    checkinstall php-cli php-curl supervisor libjpeg-dev pep8 \
    redis binutils libproj-dev gdal-bin

# Install Python requirements
cd /tmp
wget https://bootstrap.pypa.io/get-pip.py -O ./get-pip.py
python3.7 get-pip.py
cd /announcements
pip3 install -r etc/requirements.txt

# Set the Python path
cat << EOF > ~/.bashrc
export PYTHONPATH=/
EOF
source ~/.bashrc

# Migrate the database
python3.7 manage.py migrate

SCRIPT

end
