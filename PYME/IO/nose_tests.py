import numpy as np

def test_compression_lossless_uint16():
    from pymecompress import bcl
    test_data = np.random.poisson(100, 10000).reshape(100,100).astype('uint16')

    result = bcl.HuffmanDecompress(bcl.HuffmanCompress(test_data.data),
                                   test_data.nbytes).view(test_data.dtype).reshape(test_data.shape)

    assert np.allclose(result, test_data)

def test_compression_lossless_uint8():
    from pymecompress import bcl
    test_data = np.random.poisson(100, 10000).reshape(100,100).astype('uint8')

    result = bcl.HuffmanDecompress(bcl.HuffmanCompress(test_data.data),
                                   test_data.nbytes).view(test_data.dtype).reshape(test_data.shape)

    assert np.allclose(result, test_data)

def test_PZFFormat_raw_uint16():
    from PYME.IO import PZFFormat
    test_data = np.random.poisson(100, 10000).reshape(100,100).astype('uint16')

    result, header = PZFFormat.loads(PZFFormat.dumps(test_data))

    #print result

    assert np.allclose(result.squeeze(), test_data.squeeze())

def test_PZFFormat_raw_uint8():
    from PYME.IO import PZFFormat
    test_data = np.random.poisson(50, 100).reshape(10,10).astype('uint8')

    result, header = PZFFormat.loads(PZFFormat.dumps(test_data))

    #print result.squeeze(), test_data, result.shape, test_data.shape

    assert np.allclose(result.squeeze(), test_data.squeeze())

def test_PZFFormat_lossless_uint16():
    from PYME.IO import PZFFormat
    test_data = np.random.poisson(100, 10000).reshape(100,100).astype('uint16')

    result, header = PZFFormat.loads(PZFFormat.dumps(test_data, compression = PZFFormat.DATA_COMP_HUFFCODE))

    #print result

    assert np.allclose(result.squeeze(), test_data.squeeze())

def test_PZFFormat_lossy_uint16():
    from PYME.IO import PZFFormat
    test_data = np.random.poisson(100, 100).reshape(10,10).astype('uint16')

    result, header = PZFFormat.loads(PZFFormat.dumps(test_data,
                                                     compression = PZFFormat.DATA_COMP_HUFFCODE,
                                                     quantization = PZFFormat.DATA_QUANT_SQRT,
                                                     quantizationOffset=0, quantizationScale=1))

    #print result
    test_quant = (np.floor(np.sqrt(test_data.astype('f'))).astype('i'))**2

    print(test_quant.squeeze() - result.squeeze())
    print(test_data.squeeze())
    print(test_quant.squeeze())
    print(result.squeeze())

    assert np.allclose(result.squeeze(), test_quant.squeeze())

def test_PZFFormat_lossless_uint8():
    from PYME.IO import PZFFormat
    test_data = np.random.poisson(50, 100).reshape(10,10).astype('uint8')

    result, header = PZFFormat.loads(PZFFormat.dumps(test_data, compression = PZFFormat.DATA_COMP_HUFFCODE))

    #print result.squeeze(), test_data, result.shape, test_data.shape

    assert np.allclose(result.squeeze(), test_data.squeeze())