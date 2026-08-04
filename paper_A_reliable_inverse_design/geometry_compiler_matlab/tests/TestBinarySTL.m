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

        function testDirectoryFinalPathRejectedWithoutNestedArtifact(testCase)
            fixture = TestBinarySTL.tempFixture();
            finalPath = fullfile(fixture.dir, 'mesh.stl');
            mkdir(finalPath);

            testCase.verifyError(@() export_binary_stl( ...
                TestBinarySTL.tetrahedronFixture(), finalPath), ...
                'MATLABGyroid:OutputConflict');

            listing = dir(finalPath);
            testCase.verifyEmpty(listing(~[listing.isdir]));
        end

        function testCorruptHeaderRejected(testCase)
            fixture = TestBinarySTL.tempFixture();
            path = fullfile(fixture.dir, 'mesh.stl');
            mesh = TestBinarySTL.tetrahedronFixture();
            export_binary_stl(mesh, path);
            TestBinarySTL.writeSingleByte(path, 0, uint8('X'));

            testCase.verifyError(@() verify_binary_stl(path), ...
                'MATLABGyroid:STLVerificationError');
        end

        function testFinitePayloadMismatchRejectedAgainstMesh(testCase)
            fixture = TestBinarySTL.tempFixture();
            path = fullfile(fixture.dir, 'mesh.stl');
            mesh = TestBinarySTL.tetrahedronFixture();
            export_binary_stl(mesh, path);
            TestBinarySTL.writeSingleValue(path, 96, single(0.25));

            testCase.verifyError(@() verify_binary_stl(path, mesh), ...
                'MATLABGyroid:STLVerificationError');
        end

        function testFinalVerificationFailureRemovesOwnedArtifact(testCase)
            fixture = TestBinarySTL.tempFixture();
            shadowDirectory = fullfile(fixture.dir, 'shadow');
            mkdir(shadowDirectory);
            TestBinarySTL.writeTextFile(fullfile( ...
                shadowDirectory, 'verify_binary_stl.m'), sprintf([ ...
                'function summary = verify_binary_stl(path, varargin)\n' ...
                'persistent callCount; if isempty(callCount), callCount=0; end\n' ...
                'callCount=callCount+1;\n' ...
                'if callCount==1\n' ...
                'info=dir(path); summary=struct(''byte_length'',info.bytes,' ...
                '''triangle_count'',4,''all_finite'',true,' ...
                '''sha256'',repmat(''0'',1,64));\n' ...
                'else\n' ...
                'error(''MATLABGyroid:STLVerificationError'',' ...
                '''forced final verification failure'');\n' ...
                'end\nend\n']));
            addpath(shadowDirectory, '-begin');
            clear verify_binary_stl;
            pathCleanup = onCleanup(@() ...
                TestBinarySTL.removeShadow(shadowDirectory));
            finalPath = fullfile(fixture.dir, 'owned.stl');

            testCase.verifyError(@() export_binary_stl( ...
                TestBinarySTL.tetrahedronFixture(), finalPath), ...
                'MATLABGyroid:STLVerificationError');
            testCase.verifyFalse(isfile(finalPath));
            clear pathCleanup;
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

        function writeSingleByte(path, offset, value)
            fileId = fopen(path, 'r+b', 'ieee-le');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            assert(fseek(fileId, offset, 'bof') == 0);
            fwrite(fileId, value, 'uint8');
        end

        function writeSingleValue(path, offset, value)
            fileId = fopen(path, 'r+b', 'ieee-le');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            assert(fseek(fileId, offset, 'bof') == 0);
            fwrite(fileId, value, 'single');
        end

        function writeTextFile(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', value);
        end

        function removeShadow(path)
            rmpath(path);
            clear verify_binary_stl;
        end
    end
end
