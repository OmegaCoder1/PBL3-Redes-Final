// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract PostoReserva {
    struct Bloco {
        address cliente;
        int origemX;
        int origemY;
        int destinoX;
        int destinoY;
        uint bateria;
        uint timestamp;
    }

    struct Resposta {
        address servidor;
        bool sucesso;
        string motivo;
        uint timestamp;
    }

    Bloco[] public registros;
    mapping(uint => Resposta[]) public respostas;

    event NovoBloco(address cliente, uint id);
    event ReservaRespondida(uint idBloco, address servidor, bool sucesso, string motivo);

    function solicitarRegistro(
        int origemX,
        int origemY,
        int destinoX,
        int destinoY,
        uint bateria
    ) public returns (uint) {
        registros.push(Bloco(msg.sender, origemX, origemY, destinoX, destinoY, bateria, block.timestamp));
        emit NovoBloco(msg.sender, registros.length - 1);
        return registros.length - 1;
    }

    function registrarResposta(
        uint idBloco,
        bool sucesso,
        string calldata motivo
    ) public {
        require(idBloco < registros.length, "ID do bloco invalido");
        respostas[idBloco].push(Resposta(msg.sender, sucesso, motivo, block.timestamp));
        emit ReservaRespondida(idBloco, msg.sender, sucesso, motivo);
    }

    function getBloco(uint id) public view returns (Bloco memory) {
        return registros[id];
    }

    function getRespostas(uint idBloco) public view returns (Resposta[] memory) {
        return respostas[idBloco];
    }

    function registrosLength() public view returns (uint) {
        return registros.length;
    }
}
