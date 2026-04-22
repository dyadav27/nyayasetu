package main

import (
	"crypto/x509"
	"fmt"
	"log"
	"os"
	"path"
	"time"

	"github.com/hyperledger/fabric-gateway/pkg/client"
	"github.com/hyperledger/fabric-gateway/pkg/identity"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

const (
	mspID         = "Org1MSP"
	channelName   = "nyayasetu"
	chaincodeName = "evidence"
)

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	peerEndpoint := getEnv("FABRIC_PEER_ENDPOINT", "localhost:7051")
	gatewayPeer  := getEnv("FABRIC_GATEWAY_PEER",  "peer0.org1.example.com")
	cryptoBase   := getEnv("CRYPTO_PATH", path.Join(os.Getenv("HOME"),
		"go/src/github.com/Vedanttamboli17/fabric-samples/test-network/organizations"))

	cryptoPath := path.Join(cryptoBase, "organizations/peerOrganizations/org1.example.com")
	certPath   := path.Join(cryptoPath, "users/Admin@org1.example.com/msp/signcerts/cert.pem")
	keyPath    := path.Join(cryptoPath, "users/Admin@org1.example.com/msp/keystore")
	tlsPath    := path.Join(cryptoPath, "peers/peer0.org1.example.com/tls/ca.crt")

	tlsCert, err := os.ReadFile(tlsPath)
	if err != nil {
		log.Fatalf("Failed to read TLS cert: %v", err)
	}
	certPool := x509.NewCertPool()
	certPool.AppendCertsFromPEM(tlsCert)
	transportCreds := credentials.NewClientTLSFromCert(certPool, gatewayPeer)
	conn, err := grpc.Dial(peerEndpoint, grpc.WithTransportCredentials(transportCreds))
	if err != nil {
		log.Fatalf("Failed to connect to peer: %v", err)
	}
	defer conn.Close()

	certPEM, err := os.ReadFile(certPath)
	if err != nil {
		log.Fatalf("Failed to read cert: %v", err)
	}
	cert, err := identity.CertificateFromPEM(certPEM)
	if err != nil {
		log.Fatalf("Failed to parse cert: %v", err)
	}
	id, err := identity.NewX509Identity(mspID, cert)
	if err != nil {
		log.Fatalf("Failed to create identity: %v", err)
	}

	keyFiles, err := os.ReadDir(keyPath)
	if err != nil {
		log.Fatalf("Failed to read keystore: %v", err)
	}
	keyPEM, err := os.ReadFile(path.Join(keyPath, keyFiles[0].Name()))
	if err != nil {
		log.Fatalf("Failed to read key: %v", err)
	}
	privateKey, err := identity.PrivateKeyFromPEM(keyPEM)
	if err != nil {
		log.Fatalf("Failed to parse key: %v", err)
	}
	sign, err := identity.NewPrivateKeySign(privateKey)
	if err != nil {
		log.Fatalf("Failed to create signer: %v", err)
	}

	gw, err := client.Connect(
		id,
		client.WithSign(sign),
		client.WithClientConnection(conn),
		client.WithEvaluateTimeout(5*time.Second),
		client.WithEndorseTimeout(15*time.Second),
		client.WithSubmitTimeout(5*time.Second),
		client.WithCommitStatusTimeout(60*time.Second),
	)
	if err != nil {
		log.Fatalf("Failed to connect to gateway: %v", err)
	}
	defer gw.Close()

	network  := gw.GetNetwork(channelName)
	contract := network.GetContract(chaincodeName)

	fmt.Println("NyayaSetu Fabric REST API starting on :8080 ...")
	serve(contract)
}
