{ pkgs, pywm }:
let
  my-python = pkgs.python3;
  python-with-my-packages = my-python.withPackages (p: with p; [
    pywm
    pycairo
    psutil
    websockets
    python-pam
    pyfiglet
    fuzzywuzzy
  ]);
in
pkgs.python3.pkgs.buildPythonApplication rec {
  pname = "newm";
  version = "0.2";

  buildInputs = [
    python-with-my-packages
  ];

  src = ../..;

  # Skip this as it tries to start the compositor
  setuptoolsCheckPhase = "true";
}
