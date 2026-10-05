"""Probe order and dependencies (05 §3, D-03). Probes not built yet are simply absent."""
from special26.probes.p01_entity import P01Entity
from special26.probes.p02_sender import P02Sender
from special26.probes.p03_headers import P03Headers
from special26.probes.p04_fraud_notice import P04FraudNotice
from special26.probes.p07_role import P07Role
from special26.probes.p08_office import P08Office
from special26.probes.p09_image import P09Image
from special26.probes.p11_policy import P11Policy

PROBES = [P01Entity, P11Policy, P03Headers, P02Sender, P04FraudNotice, P07Role, P08Office, P09Image]
