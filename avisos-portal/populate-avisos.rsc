# populate-avisos.rsc - Agrega TODOS los clientes PPPoE activos al address-list "avisos"
# Se ejecuta cada 5 minutos via scheduler
# Excluye solo clientes que ya vieron el aviso (avisos-visto, rastreado por nombre)

:foreach i in=[/ppp active find] do={
  :local addr [/ppp active get $i address]
  :local uname [/ppp active get $i name]
  :if ([:len [/ip firewall address-list find where list=avisos address=$addr]] = 0) do={
    :if ([:len [/ip firewall address-list find where list="avisos-visto" comment=$uname]] = 0) do={
      /ip firewall address-list add list=avisos address=$addr comment=$uname
    }
  }
}
