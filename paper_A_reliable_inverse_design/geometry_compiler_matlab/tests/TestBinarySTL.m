classdef TestBinarySTL < matlab.unittest.TestCase
%TESTBINARYSTL Tests deterministic binary STL serialization.

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(fileparts(testFile));
            addpath(fullfile(testCase.BaseDir, 'core'));
        end
    end

    methods (Test)
        function testTetrahedronRoundTripIsDeterministic(testCase)
            fixture = TestBinarySTL.tempFixture();
            firstPath = fullfile(fixture.dir, 'first.stl');
            secondPath = fullfile(fixture.dir, 'second.stl');
            mesh = TestBinarySTL.tetrahedronFixture();

            first = export_binary_stl(mesh, firstPath);
            second = export_binary_stl(mesh, secondPath);

            testCase.verifyEqual(first.byte_length, 84 + 50 * 4);
            testCase.verifyEqual(first.triangle_count, 4);
            testCase.verifyTrue(first.all_finite);
            testCase.verifyEqual(first.sha256, second.sha256);
            testCase.verifyEqual(first, verify_binary_stl(firstPath));
        end

        function testExistingFinalPathIsNeverOverwritten(testCase)
            fixture = TestBinarySTL.tempFixture();
            finalPath = fullfile(fixture.dir, 'mesh.stl');
            mesh = TestBinarySTL.tetrahedronFixture();
            export_binary_stl(mesh, finalPath);

            testCase.verifyError(@() export_binary_stl(mesh, finalPath), ...
                'MATLABGyroid:OutputConflict');
        end

        function testTruncatedBinaryStlRejected(testCase)
            fixture = TestBinarySTL.tempFixture();
            validPath = fullfile(fixture.dir, 'valid.stl');
            corruptPath = fullfile(fixture.dir, 'corrupt.stl');
            export_binary_stl( ...
                TestBinarySTL.tetrahedronFixture(), validPath);
            bytes = TestBinarySTL.readBytes(validPath);
            TestBinarySTL.writeBytes(corruptPath, bytes(1:end - 1));

            testCase.verifyError(@() verify_binary_stl(corruptPath), ...
                'MATLABGyroid:STLVerificationError');
        end

        function testDegenerateTriangleRejectedByExporter(testCase)
            fixture = TestBinarySTL.tempFixture();
            mesh.vertices = [0 0 0;1 0 0;2 0 0];
            mesh.faces = [1 2 3];
            lastwarn('');
            testCase.verifyError(@() export_binary_stl(mesh, ...
                fullfile(fixture.dir, 'bad.stl')), ...
                'MATLABGyroid:STLSerializationError');
            [warningMessage, warningId] = lastwarn;
            testCase.verifyEmpty(warningMessage);
            testCase.verifyEmpty(warningId);
        end
    end

    methods (Static, Access = private)
        function fixture = tempFixture()
            fixture.dir = tempname;
            mkdir(fixture.dir);
            fixture.cleanup = onCleanup(@() rmdir(fixture.dir, 's'));
        end

        function mesh = tetrahedronFixture()
            mesh.vertices = [0 0 0;1 0 0;0 1 0;0 0 1];
            mesh.faces = [1 3 2;1 2 4;2 3 4;3 1 4];
        end

        function bytes = readBytes(path)
            fileId = fopen(path, 'rb');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            bytes = fread(fileId, Inf, '*uint8');
        end

        function writeBytes(path, bytes)
            fileId = fopen(path, 'wb');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fwrite(fileId, bytes, 'uint8');
        end
    end
end
