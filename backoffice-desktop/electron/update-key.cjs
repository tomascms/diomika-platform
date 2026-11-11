// Chave pública Ed25519 que assina os manifestos de actualização (SEG-16). A privada está só no PC de quem publica
// (deploy/update_signing.py). Trocar a chave exige uma versão nova assinada com a antiga.
module.exports = `-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAiszI86DcwsdBO0N09AcoHRLE8ccDofT/vYQgPYKgvz4=
-----END PUBLIC KEY-----
`
